"""JSON to Fritzing native parts, views, and connected wire instances.

The interchange format follows fritzing-app 5aa56a510183c23084990a6b4481708cad24c15b:
model/modelpart.cpp, connectors/connectoritem.cpp, items/wire.cpp and
mainwindow/mainwindow.cpp::saveBundledAux. No upstream source is copied here.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
import shutil
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from .routing import route_view, validate_geometry

PX_PER_MM = 90.0 / 25.4
SCHEMATIC_GRID = 2.54
# Upstream rectangle_pcb.svg uses a 0.2032 mm outline stroke inset by half.
# Compensate its bounding size so the Gerber cutter centreline matches JSON.
STOCK_BOARD_STROKE_MM = .2032
VIEWS = ("breadboardView", "schematicView", "pcbView")
LAYERS = {"breadboardView": "breadboard", "schematicView": "schematic", "pcbView": "copper0"}
WIRE_LAYERS = {"breadboardView": "breadboardWire", "schematicView": "schematicTrace", "pcbView": "copper0trace"}
FLAGS = {"breadboardView": 64, "schematicView": 128, "pcbView": 4}
ID = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,31}$")


def number(value, context, low=0, high=1000):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{context} must be a finite number from {low} to {high}")
    return float(value)


def text(value, context, limit=64):
    if not isinstance(value, str) or not value.strip() or len(value) > limit or any(ord(c) < 32 for c in value):
        raise ValueError(f"Invalid {context}: expected nonempty printable text, max {limit} characters")
    return value


def unique_id(value, context):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise ValueError(f"Invalid {context}: use a letter followed by letters, digits, underscore or hyphen")
    return value


def check_keys(obj, required, allowed, context):
    if not isinstance(obj, dict):
        raise ValueError(f"{context} must be an object")
    if set(obj) - set(allowed):
        raise ValueError(f"Unknown fields in {context}: {sorted(set(obj)-set(allowed))}")
    if set(required) - set(obj):
        raise ValueError(f"Missing fields in {context}: {sorted(set(required)-set(obj))}")


def normalize(data):
    check_keys(data, ("schema_version", "name", "parts", "nets", "board"), ("schema_version", "name", "parts", "nets", "board", "unconnected"), "design")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise ValueError("Only schema_version 1 is supported")
    d = json.loads(json.dumps(data, allow_nan=False))
    unique_id(d["name"], "design name")
    b = d["board"]
    check_keys(b, ("width_mm", "height_mm"), ("width_mm", "height_mm", "grid_mm", "trace_width_mm", "clearance_mm", "edge_clearance_mm"), "board")
    defaults = {"grid_mm": .254, "trace_width_mm": .508, "clearance_mm": .254, "edge_clearance_mm": 1.0}
    for k, v in defaults.items(): b.setdefault(k, v)
    for k in b: b[k] = number(b[k], "board."+k, .01, 500)
    if b["width_mm"] / b["grid_mm"] * b["height_mm"] / b["grid_mm"] > 1_000_000:
        raise ValueError("Routing grid exceeds one million cells; increase grid_mm")
    if not isinstance(d["parts"], list) or not 1 <= len(d["parts"]) <= 100:
        raise ValueError("parts must contain 1 to 100 parts")
    refs = set(); pins = {}
    next_x = 5.08; next_y = 5.08; row_height = 0
    for part in d["parts"]:
        check_keys(part, ("ref", "kind", "value", "pins", "body"), ("ref", "kind", "value", "pins", "body", "pcb", "schematic", "pad_diameter_mm", "drill_mm", "description"), "part")
        ref = unique_id(part["ref"], "part ref")
        if ref in refs: raise ValueError(f"Duplicate part ref: {ref}")
        refs.add(ref)
        if part["kind"] not in ("resistor", "capacitor", "led", "header", "dip", "generic"):
            raise ValueError(f"Unsupported kind for {ref}")
        text(part["value"], ref+" value", 40)
        if "description" in part: text(part["description"], "description", 200)
        check_keys(part["body"], ("width_mm", "height_mm"), ("width_mm", "height_mm"), ref+" body")
        for k in part["body"]: part["body"][k] = number(part["body"][k], ref+"."+k, .1, 100)
        part["pad_diameter_mm"] = number(part.get("pad_diameter_mm", 1.8), ref+" pad diameter", .2, 10)
        part["drill_mm"] = number(part.get("drill_mm", .9), ref+" drill", .1, 8)
        if part["drill_mm"] >= part["pad_diameter_mm"]:
            raise ValueError(f"{ref}: drill must be smaller than pad diameter")
        if not isinstance(part["pins"], list) or not 1 <= len(part["pins"]) <= 64:
            raise ValueError(f"{ref}: pins must contain 1 to 64 entries")
        if part["kind"] in ("resistor", "capacitor", "led") and len(part["pins"]) != 2:
            raise ValueError(f"{ref}: discrete symbol requires exactly two pins")
        seen = set()
        for idx, pin in enumerate(part["pins"]):
            check_keys(pin, ("id", "name", "x_mm", "y_mm"), ("id", "name", "x_mm", "y_mm"), ref+" pin")
            pid = text(pin["id"], "pin ID", 16)
            if not re.fullmatch(r"[A-Za-z0-9_-]+", pid): raise ValueError("Pin IDs cannot contain dots or whitespace")
            text(pin["name"], "pin name", 16)
            if pid in seen: raise ValueError(f"Duplicate pin {ref}.{pid}")
            seen.add(pid)
            for k in ("x_mm", "y_mm"): pin[k] = number(pin[k], ref+"."+pid+"."+k, 0, 100)
            r = part["pad_diameter_mm"] / 2
            if not r <= pin["x_mm"] <= part["body"]["width_mm"]-r or not r <= pin["y_mm"] <= part["body"]["height_mm"]-r:
                raise ValueError(f"{ref}.{pid}: full pad must fit inside footprint bounding box (body)")
            pin["connector"] = f"connector{idx}"
            pins[ref+"."+pid] = pin
        for i, pa in enumerate(part["pins"]):
            for pb in part["pins"][:i]:
                if math.hypot(pa["x_mm"]-pb["x_mm"], pa["y_mm"]-pb["y_mm"]) < max(part["drill_mm"] + .1, part["pad_diameter_mm"]):
                    raise ValueError(f"{ref}: physical pads or drill holes overlap, or holes lack 0.1 mm web")
        if "pcb" not in part:
            w,h = part["body"]["width_mm"], part["body"]["height_mm"]
            if next_x + w + 5.08 > b["width_mm"]:
                next_x = 5.08; next_y += row_height + 7.62; row_height = 0
            part["pcb"] = {"x_mm":next_x, "y_mm":next_y}
            next_x += math.ceil((w+7.62)/b["grid_mm"])*b["grid_mm"]
            row_height = max(row_height,h)
        for view in ("pcb", "schematic"):
            if view not in part: continue
            check_keys(part[view], ("x_mm", "y_mm"), ("x_mm", "y_mm"), ref+" "+view)
            for k in part[view]: part[view][k] = number(part[view][k], ref+" "+view+" "+k, 0, 1000)
    if not isinstance(d["nets"], list) or len(d["nets"]) > 200:
        raise ValueError("nets must be a list with at most 200 nets")
    net_names=set(); assigned=set()
    for net in d["nets"]:
        check_keys(net, ("name", "pins"), ("name", "pins"), "net")
        unique_id(net["name"], "net name")
        if net["name"] in net_names: raise ValueError("Duplicate net name: "+net["name"])
        net_names.add(net["name"])
        if not isinstance(net["pins"], list) or len(net["pins"]) < 2: raise ValueError("Each net requires at least two pins")
        for pin in net["pins"]:
            if not isinstance(pin, str) or pin not in pins: raise ValueError(f"Unknown pin: {pin}")
            if pin in assigned: raise ValueError(f"Pin assigned more than once: {pin}")
            assigned.add(pin)
    if not isinstance(d.get("unconnected", []),list): raise ValueError("unconnected must be a list")
    for pin in d.get("unconnected", []):
        if not isinstance(pin,str) or pin not in pins or pin in assigned: raise ValueError(f"Invalid or duplicate unconnected pin: {pin}")
        assigned.add(pin)
    if assigned != set(pins): raise ValueError("Pins must be assigned to a net or explicitly unconnected: "+", ".join(sorted(set(pins)-assigned)))
    return d


def fmt(v): return f"{v:.8g}"


def xml_bytes(root):
    ET.indent(root)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def sub(root, tag, **attrs): return ET.SubElement(root, tag, {k:str(v) for k,v in attrs.items()})


def svg_start(w,h):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{fmt(w)}mm" height="{fmt(h)}mm" viewBox="0 0 {fmt(w)} {fmt(h)}">'


def label(x,y,s,size=2,anchor="middle",fill="#222222",max_width=None):
    if max_width is not None:
        size = min(size, max_width / max(1, len(s)) / 1.1)
    return f'<text x="{fmt(x)}" y="{fmt(y)}" font-family="DejaVu Sans" font-size="{fmt(size)}" text-anchor="{anchor}" fill="{fill}">{escape(s)}</text>'


def schematic(part):
    discrete = part["kind"] in ("resistor","capacitor","led")
    count = len(part["pins"])
    nleft=(count+1)//2
    if discrete: w,h=30.48,20.32; points=[(0,12.7),(30.48,12.7)]
    elif part["kind"] == "header":
        longest = max(len(p["name"]) for p in part["pins"])
        w = max(30.48, math.ceil((longest*1.6+12)/SCHEMATIC_GRID)*SCHEMATIC_GRID)
        h = max(25.4, (count+3)*5.08)
        points = [(w, 12.7+i*5.08) for i in range(count)]
    else:
        longest = max(len(p["name"]) for p in part["pins"])
        w = max(40.64, math.ceil((longest*2.4+15)/SCHEMATIC_GRID)*SCHEMATIC_GRID)
        h = max(25.4, (nleft+3)*5.08)
        points=[(0, (i+3)*5.08) if i<nleft else (w,(i-nleft+3)*5.08) for i in range(count)]
    a=[svg_start(w,h),'<g id="schematic">',label(w/2,3.5,part["ref"],2.6,max_width=w-5.08),label(w/2,7,part["value"],2,max_width=w-5.08)]
    if discrete:
        if part["kind"]=="resistor":
            a.append('<rect x="10.16" y="10.16" width="10.16" height="5.08" fill="white" stroke="#222" stroke-width="0.5"/>')
            body_left,body_right=10.16,20.32
        elif part["kind"]=="capacitor":
            a.append('<path d="M13.97 8.89 V16.51 M16.51 8.89 V16.51" fill="none" stroke="#222" stroke-width="0.5"/>')
            body_left,body_right=13.97,16.51
        else:
            a.append('<path d="M11.43 8.89 L11.43 16.51 L17.78 12.7 Z M17.78 8.89 V16.51 M19.05 9.5 L22.86 5.7 M21.6 9.5 L25.4 5.7 M20.7 5.7 L22.86 5.7 L22.86 7.86 M23.24 5.7 L25.4 5.7 L25.4 7.86" fill="none" stroke="#222" stroke-width="0.5"/>')
            body_left,body_right=11.43,17.78
        for idx,(x,y) in enumerate(points):
            end=body_left if idx==0 else body_right
            a.append(f'<line id="connector{idx}pin" x1="{x}" y1="{y}" x2="{end}" y2="{y}" stroke="#222" stroke-width="0.5"/>')
            a.append(f'<rect id="connector{idx}terminal" x="{x-.05}" y="{y-.05}" width="0.1" height="0.1" fill="none"/>')
            a.append(label(2 if idx==0 else w-2,11.2,part["pins"][idx]["name"],1.5,"start" if idx==0 else "end",max_width=8))
    else:
        a.append(f'<rect x="5.08" y="10.16" width="{fmt(w-10.16)}" height="{fmt(h-11.43)}" fill="white" stroke="#222" stroke-width=".4"/>')
        for idx,(x,y) in enumerate(points):
            left=x==0; end=5.08 if left else w-5.08
            a.append(f'<line id="connector{idx}pin" x1="{fmt(x)}" y1="{fmt(y)}" x2="{fmt(end)}" y2="{fmt(y)}" stroke="#222" stroke-width=".4"/>')
            a.append(f'<rect id="connector{idx}terminal" x="{fmt(x-.05)}" y="{fmt(y-.05)}" width=".1" height=".1" fill="none"/>')
            a.append(label(end+(1 if left else -1),y-.8,part["pins"][idx]["name"],1.7,"start" if left else "end",max_width=(w-12.16) if part["kind"] == "header" else (w-12.16)/2))
    a += ['</g></svg>']
    return "".join(a),w,h,points


def silkscreen(part):
    """Trim the outline around exposed pads and place a label only in clear area."""
    w,h=part["body"]["width_mm"],part["body"]["height_mm"]
    inset=min(.3,w/4,h/4);radius=part["pad_diameter_mm"]/2+.325
    pieces=['<g id="silkscreen">']
    for horizontal,constant,start,end in ((True,inset,inset,w-inset),(True,h-inset,inset,w-inset),(False,inset,inset,h-inset),(False,w-inset,inset,h-inset)):
        intervals=[(start,end)]
        for p in part["pins"]:
            across=p["y_mm"] if horizontal else p["x_mm"];along=p["x_mm"] if horizontal else p["y_mm"]
            delta=abs(across-constant)
            if delta>=radius:continue
            half=math.sqrt(radius*radius-delta*delta);lo,hi=along-half,along+half
            new=[]
            for a,b in intervals:
                if b<=lo or a>=hi:new.append((a,b))
                else:
                    if a<lo:new.append((a,lo))
                    if b>hi:new.append((hi,b))
            intervals=new
        for a,b in intervals:
            if b-a<.15:continue
            x1,y1,x2,y2=(a,constant,b,constant) if horizontal else (constant,a,constant,b)
            pieces.append(f'<line x1="{fmt(x1)}" y1="{fmt(y1)}" x2="{fmt(x2)}" y2="{fmt(y2)}" stroke="#222222" stroke-width=".15"/>')
    placed=False
    for size in (1.0,.8,.6):
        tw=len(part["ref"])*size*1.1
        for baseline in (h/2+size*.35,inset+.3+size,h-inset-.3):
            x0,y0,x1,y1=w/2-tw/2,baseline-size*1.2,w/2+tw/2,baseline+size*.2
            if x0<inset+.2 or y0<inset+.1 or x1>w-inset-.2 or y1>h-inset-.1:continue
            if any(math.hypot(max(x0-p["x_mm"],0,p["x_mm"]-x1),max(y0-p["y_mm"],0,p["y_mm"]-y1)) < radius for p in part["pins"]):continue
            pieces.append(label(w/2,baseline,part["ref"],size));placed=True;break
        if placed:break
    pieces.append('</g>')
    return ''.join(pieces)


def part_files(part):
    sch,w,h,spoints=schematic(part)
    pw,ph=part["body"]["width_mm"],part["body"]["height_mm"]
    pd,dr=part["pad_diameter_mm"],part["drill_mm"]
    ring=(pd-dr)/2; radius=(pd+dr)/4
    pcb=[svg_start(pw,ph),silkscreen(part),'<g id="copper1"><g id="copper0">']
    body_color={"resistor":"#e5d7bb","led":"#eaa3a0","capacitor":"#94b6d9","header":"#343b43","dip":"#343b43","generic":"#c0cad4"}[part["kind"]]
    text_color="white" if part["kind"] in ("header","dip") else "#222222"
    bb=[svg_start(pw,ph),'<g id="breadboard">',f'<rect x=".15" y=".15" width="{fmt(pw-.3)}" height="{fmt(ph-.3)}" rx=".5" fill="{body_color}" stroke="#333" stroke-width=".2"/>']
    for i,p in enumerate(part["pins"]):
        x,y=fmt(p["x_mm"]),fmt(p["y_mm"])
        pcb.append(f'<circle id="connector{i}pin" cx="{x}" cy="{y}" r="{fmt(radius)}" fill="none" stroke="#f7bd13" stroke-width="{fmt(ring)}"/>')
        bb.append(f'<circle id="connector{i}pin" cx="{x}" cy="{y}" r="{fmt(pd/2)}" fill="#aaaaaa" stroke="#555" stroke-width=".15"/>')
    bb.append(label(pw/2,1.3,part["ref"],1.2,fill=text_color,max_width=pw-1))
    pcb.append('</g></g></svg>');bb.append('</g></svg>')
    digest=hashlib.sha256((json.dumps(part,sort_keys=True)+sch+"".join(pcb)+"".join(bb)).encode()).hexdigest()[:20]
    mid=f"Engineering_{part['ref']}_{digest}"
    module=ET.Element("module",{"moduleId":mid,"fritzingVersion":"1.0.1"})
    for tag,value in (("version","1"),("author","Engineering Codex Workbench"),("title",part["ref"]+" "+part["value"]),("label",part["ref"]),("date","2026-11-10"),("description",part.get("description","Explicit user-defined through-hole footprint; verify against component datasheet."))):sub(module,tag).text=value
    props=sub(module,"properties")
    for name,value in (("family","Engineering custom part"),("package",part["kind"]),("value",part["value"])):sub(props,"property",name=name).text=value
    views=sub(module,"views")
    for view,folder,layers in (("iconView","icon",["icon"]),("breadboardView","breadboard",["breadboard"]),("schematicView","schematic",["schematic"]),("pcbView","pcb",["copper0","copper1","silkscreen"])):
        ls=sub(sub(views,view),"layers",image=f"{folder}/{mid}_{folder}.svg")
        for layer in layers:sub(ls,"layer",layerId=layer)
    connectors=sub(module,"connectors")
    for i,p in enumerate(part["pins"]):
        con=sub(connectors,"connector",id=f"connector{i}",name=p["name"],type="male");sub(con,"description").text=p["id"]+" "+p["name"]
        vs=sub(con,"views")
        for view,layers in (("breadboardView",["breadboard"]),("schematicView",["schematic"]),("pcbView",["copper0","copper1"])):
            v=sub(vs,view)
            for layer in layers:
                attrs={"layer":layer,"svgId":f"connector{i}pin"}
                if view=="schematicView": attrs["terminalId"]=f"connector{i}terminal"
                sub(v,"p",**attrs)
    files={f"part.{mid}.fzp":xml_bytes(module),f"svg.schematic.{mid}_schematic.svg":sch.encode(),f"svg.pcb.{mid}_pcb.svg":"".join(pcb).encode(),f"svg.breadboard.{mid}_breadboard.svg":"".join(bb).encode(),f"svg.icon.{mid}_icon.svg":"".join(bb).replace('id="breadboard"', 'id="icon"').encode()}
    return mid,files,{"width":w,"height":h,"pins":spoints}


def rect_overlap(a,b,margin=0):
    return a[0] < b[2]+margin and a[2]+margin>b[0] and a[1]<b[3]+margin and a[3]+margin>b[1]


def prepare_layout(d):
    files={}; modules={}; shapes={}
    for p in d["parts"]:
        mid,pfiles,shape=part_files(p); modules[p["ref"]]=mid; files.update(pfiles);shapes[p["ref"]]=shape
    maxw=max(s["width"] for s in shapes.values());maxh=max(s["height"] for s in shapes.values())
    for idx,p in enumerate(d["parts"]):
        p.setdefault("schematic",{"x_mm":10.16+(idx%3)*(maxw+20.32),"y_mm":10.16+(idx//3)*(maxh+20.32)})
    net_by_pin={pin:n["name"] for n in d["nets"] for pin in n["pins"]}
    layouts={}
    for view in VIEWS:
        is_pcb=view=="pcbView"; sch=view=="schematicView"
        pins={};rects=[];positions={}; obstacles=[]
        for idx,p in enumerate(d["parts"]):
            shape=shapes[p["ref"]]
            if is_pcb:
                x,y=p["pcb"]["x_mm"],p["pcb"]["y_mm"];w,h=p["body"]["width_mm"],p["body"]["height_mm"]
                points=[(q["x_mm"],q["y_mm"]) for q in p["pins"]]
            elif sch:
                x,y=p["schematic"]["x_mm"],p["schematic"]["y_mm"];w,h=shape["width"],shape["height"];points=shape["pins"]
                obstacles.append((x+2.54,y,x+w-2.54,y+h))
            else:
                # Functional assembly overview: authentic footprint-scale custom parts.
                x,y=p["pcb"]["x_mm"],p["pcb"]["y_mm"];w,h=p["body"]["width_mm"],p["body"]["height_mm"]
                points=[(q["x_mm"],q["y_mm"]) for q in p["pins"]]
            r=(x,y,x+w,y+h)
            if is_pcb and (x < 0 or y < 0 or x+w > d["board"]["width_mm"]+1e-8 or y+h > d["board"]["height_mm"]+1e-8):
                raise ValueError(f"PCB footprint bounding box outside board: {p['ref']}")
            for other,oref in rects:
                if rect_overlap(r,other, .5 if is_pcb else 1): raise ValueError(f"{view}: component/label bounding boxes overlap: {p['ref']} and {oref}")
            rects.append((r,p["ref"]));positions[p["ref"]]={"x":x,"y":y,"width":w,"height":h}
            for pin,point in zip(p["pins"],points):
                key=p["ref"]+"."+pin["id"]
                pins[key]={"x":x+point[0],"y":y+point[1],"radius":.3 if sch else p["pad_diameter_mm"]/2,"net":net_by_pin.get(key,"NC_"+key)}
        b=d["board"]
        width=b["width_mm"] if not sch else max(r[0][2] for r in rects)+10.16
        height=b["height_mm"] if not sch else max(r[0][3] for r in rects)+10.16
        params={"width":width,"height":height,"grid":SCHEMATIC_GRID if sch else b["grid_mm"],"clearance":1 if sch else b["clearance_mm"],"trace_width":.45 if sch else b["trace_width_mm"],"edge_clearance":2.54 if sch else b["edge_clearance_mm"],"obstacles":obstacles}
        route_nets = d["nets"] + [{"name": "NC_"+pin, "pins": [pin]} for pin in d.get("unconnected", [])]
        result=route_view(pins,route_nets,**params)
        if result.get("errors"):raise ValueError(f"{view}: "+"; ".join(result["errors"]))
        layouts[view]={"pins":pins,"parts":positions,"segments":result["segments"],"rules":params}
    return files,modules,layouts


def instance(parent,mid,idx,title,path):
    inst=sub(parent,"instance",moduleIdRef=mid,modelIndex=idx,path=path);sub(inst,"title").text=title
    return inst


def project_xml(d,modules,layouts):
    root=ET.Element("module",{"fritzingVersion":"1.0.1"})
    views=sub(root,"views")
    for name in VIEWS:
        attrs={"name":name,"backgroundColor":"#ffffff","gridSize":"0.1in","showGrid":"0","alignToGrid":"1","viewFromBelow":"0"}
        if name=="pcbView":attrs["DRC_Keepout"]=fmt(d["board"]["clearance_mm"])+"mm"
        sub(views,"view",**attrs)
    instances=sub(root,"instances");indices={p["ref"]:i+1 for i,p in enumerate(d["parts"])};viewnodes={};con_nodes={}
    for p in d["parts"]:
        inst=instance(instances,modules[p["ref"]],indices[p["ref"]],p["ref"],modules[p["ref"]]+".fzp")
        sub(inst,"property",name="value",value=p["value"])
        vs=sub(inst,"views")
        for view in VIEWS:
            v=sub(vs,view,layer=LAYERS[view]);pos=layouts[view]["parts"][p["ref"]]
            sub(v,"geometry",x=fmt(pos["x"]*PX_PER_MM),y=fmt(pos["y"]*PX_PER_MM),z="5.5" if view=="pcbView" else "2.5")
            viewnodes[(indices[p["ref"]],view)]=v
    board=instance(instances,"RectanglePCBModuleID",len(indices)+1,"PCB1","rectangle_pcb.fzp")
    for name,value in (("layers",1),("width",d["board"]["width_mm"]+STOCK_BOARD_STROKE_MM),("height",d["board"]["height_mm"]+STOCK_BOARD_STROKE_MM)):sub(board,"property",name=name,value=value)
    sub(sub(sub(board,"views"),"pcbView",layer="board"),"geometry",x=fmt(-STOCK_BOARD_STROKE_MM/2*PX_PER_MM),y=fmt(-STOCK_BOARD_STROKE_MM/2*PX_PER_MM),z="0.5")
    nextidx=len(indices)+2
    def con(idx,view,cid,layer):
        key=(idx,view,cid,layer)
        if key not in con_nodes:
            parent=viewnodes[(idx,view)];cs=parent.find("connectors")
            if cs is None:cs=sub(parent,"connectors")
            cn=sub(cs,"connector",connectorId=cid,layer=layer);sub(cn,"geometry",x="0",y="0");con_nodes[key]=sub(cn,"connects")
        return con_nodes[key]
    def connect(a,b,view):
        ia,ca,la=a;ib,cb,lb=b
        sub(con(ia,view,ca,la),"connect",modelIndex=ib,connectorId=cb,layer=lb)
    for view in VIEWS:
        endpoints={}
        for p in d["parts"]:
            for pin in p["pins"]:
                key=p["ref"]+"."+pin["id"]; xy=layouts[view]["pins"][key]
                point=(round(xy["x"],7),round(xy["y"],7),xy["net"])
                endpoints.setdefault(point,[]).append((indices[p["ref"]],pin["connector"],LAYERS[view]))
        for seg in layouts[view]["segments"]:
            idx=nextidx;nextidx+=1
            inst=instance(instances,"WireModuleID",idx,seg["net"],"wire.fzp")
            v=sub(sub(inst,"views"),view,layer=WIRE_LAYERS[view]);viewnodes[(idx,view)]=v
            a,b=seg["a"],seg["b"]
            sub(v,"geometry",x=fmt(a[0]*PX_PER_MM),y=fmt(a[1]*PX_PER_MM),x1="0",y1="0",x2=fmt((b[0]-a[0])*PX_PER_MM),y2=fmt((b[1]-a[1])*PX_PER_MM),z="4.5",wireFlags=FLAGS[view])
            sub(v,"wireExtras",mils=fmt(layouts[view]["rules"]["trace_width"]/25.4*1000),color="#222222" if view=="schematicView" else ("#d28a00" if view=="pcbView" else "#2672a6"),opacity="1",banded="0")
            for n,pt in enumerate((a,b)):
                endpoints.setdefault((round(pt[0],7),round(pt[1],7),seg["net"]),[]).append((idx,"connector"+str(n),WIRE_LAYERS[view]))
        for connected in endpoints.values():
            for a in connected:
                for b in connected:
                    if a!=b:connect(a,b,view)
    return xml_bytes(root)


def zip_bytes(files):
    bio=io.BytesIO()
    with zipfile.ZipFile(bio,"w",zipfile.ZIP_DEFLATED) as z:
        for name,data in sorted(files.items()):
            zi=zipfile.ZipInfo(name,(2026,1,1,0,0,0));zi.compress_type=zipfile.ZIP_DEFLATED;zi.external_attr=0o644<<16;z.writestr(zi,data)
    return bio.getvalue()


def generate(data, output):
    output=Path(output)
    if output.exists() and any(output.iterdir()): raise ValueError("Output directory must be empty; use a fresh directory to avoid stale exports")
    d=normalize(data)
    files,modules,layouts=prepare_layout(d)
    fz=project_xml(d,modules,layouts)
    manifest={"schema_version":1,"name":d["name"],"design":d,"modules":modules,"layout":layouts}
    files["project.fz"]=fz
    # Exact generated members are verified on validation; this is integrity, not authentication.
    manifest["members_sha256"]={n:hashlib.sha256(b).hexdigest() for n,b in files.items()}
    files["engineering-manifest.json"]=json.dumps(manifest,indent=2).encode()
    fzz=zip_bytes(files)
    report=validate_archive_bytes(fzz)
    if not report["passed"]:raise ValueError("Generated project validation failed: "+"; ".join(report["errors"]))
    output.parent.mkdir(parents=True,exist_ok=True)
    temp=Path(tempfile.mkdtemp(prefix=".fritzing-",dir=output.parent))
    try:
        (temp/"project.fzz").write_bytes(fzz);(temp/"project.fz").write_bytes(fz)
        # Preserve user input, not internal normalized connector annotations.
        (temp/"design.json").write_text(json.dumps(data,indent=2,allow_nan=False)+"\n")
        (temp/"layout.json").write_text(json.dumps(layouts,indent=2)+"\n")
        (temp/"validation.json").write_text(json.dumps(report,indent=2)+"\n")
        (temp/"parts").mkdir();(temp/"parts"/"source").mkdir()
        for p in d["parts"]:
            mid=modules[p["ref"]];pf={n:b for n,b in files.items() if mid in n}
            (temp/"parts"/(p["ref"]+".fzpz")).write_bytes(zip_bytes(pf))
            for name,content in pf.items():(temp/"parts"/"source"/name).write_bytes(content)
        with (temp/"bom.csv").open("w",newline="") as f:
            writer=csv.writer(f);writer.writerow(["Reference","Value","Kind","Pins","Pad diameter (mm)","Drill (mm)"])
            for p in d["parts"]:writer.writerow([p["ref"],p["value"],p["kind"],len(p["pins"]),p["pad_diameter_mm"],p["drill_mm"]])
        if output.exists():output.rmdir()
        temp.rename(output)
    finally:
        if temp.exists():shutil.rmtree(temp)
    return report


def validate_archive_bytes(blob):
    errors=[]
    def fail(message):errors.append(message)
    try:
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            names=z.namelist()
            if len(set(names))!=len(names):raise ValueError("Duplicate archive members")
            if len(names)>1000 or any(i.file_size>20_000_000 for i in z.infolist()) or sum(i.file_size for i in z.infolist())>100_000_000:raise ValueError("Archive exceeds validation resource limits")
            if any('/' in n or '\\' in n or n in ('.','..') for n in names):raise ValueError("Archive members must be flat safe filenames")
            if "engineering-manifest.json" not in names:raise ValueError("Validation supports workbench-generated FZZ only; arbitrary FZZ requires native Fritzing checks")
            manifest=json.loads(z.read("engineering-manifest.json"));expected=manifest["members_sha256"]
            if set(names)!=set(expected)|{"engineering-manifest.json"}:fail("Archive member inventory does not match manifest")
            for name,digest in expected.items():
                if name not in names or hashlib.sha256(z.read(name)).hexdigest()!=digest:fail("Modified or missing member: "+name)
            root=ET.fromstring(z.read("project.fz"))
            instances={i.get("modelIndex"):i for i in root.findall("./instances/instance")}
            if len(instances)!=len(root.findall("./instances/instance")):fail("Duplicate modelIndex")
            modules={}
            for name in names:
                if name.startswith("part.") and name.endswith(".fzp"):
                    part=ET.fromstring(z.read(name));modules[part.get("moduleId")]=part
                    for layers in part.findall("./views/*/layers"):
                        folder,filename=layers.get("image","").split("/",1);svgname="svg."+folder+"."+filename
                        if svgname not in names:fail("Missing SVG: "+svgname);continue
                        svg=ET.fromstring(z.read(svgname));ids={e.get("id") for e in svg.iter()}
                        view=next(v.tag for v in part.findall("./views/*") if v.find("layers") is layers)
                        for p in part.findall("./connectors/connector/views/"+view+"/p"):
                            for attr in ("svgId","terminalId"):
                                if p.get(attr) and p.get(attr) not in ids:fail(f"Missing connector SVG ID {p.get(attr)} in {svgname}")
            # Build actual saved electrical connectivity for each view, independently.
            parts_by_ref={p["ref"]:p for p in manifest["design"]["parts"]}
            index_by_ref={i.findtext("title"):idx for idx,i in instances.items() if i.get("moduleIdRef") in modules}
            for view in VIEWS:
                adjacency={};saved_edges=set()
                for idx,inst in instances.items():
                    v=inst.find("./views/"+view)
                    if v is None:continue
                    is_wire=inst.get("moduleIdRef")=="WireModuleID"
                    if is_wire:
                        a=(idx,"connector0");b=(idx,"connector1");adjacency.setdefault(a,set()).add(b);adjacency.setdefault(b,set()).add(a)
                        if int(v.find("geometry").get("wireFlags","0"))!=FLAGS[view]:fail("Wrong wire flags in "+view)
                    elif inst.get("moduleIdRef") not in modules and inst.get("moduleIdRef")!="RectanglePCBModuleID":fail("Unknown part module")
                    for c in v.findall("./connectors/connector"):
                        a=(idx,c.get("connectorId"));adjacency.setdefault(a,set())
                        for conn in c.findall("./connects/connect"):
                            b=(conn.get("modelIndex"),conn.get("connectorId"));adjacency[a].add(b);saved_edges.add((a,b))
                            target=instances.get(b[0]);targetview=None if target is None else target.find("./views/"+view)
                            if targetview is None:fail("Connection refers to missing instance/view")
                for a,b in saved_edges:
                    if (b,a) not in saved_edges:fail("Nonreciprocal connector reference in "+view)
                net_groups=[]
                for net in manifest["design"]["nets"]:
                    terminals=[]
                    for pname in net["pins"]:
                        ref,pid=pname.split(".");part=parts_by_ref[ref];pin=next(q for q in part["pins"] if q["id"]==pid)
                        terminals.append((index_by_ref[ref],pin["connector"]))
                    reached=set();queue=[terminals[0]]
                    while queue:
                        a=queue.pop()
                        if a in reached:continue
                        reached.add(a);queue.extend(adjacency.get(a,()))
                    if not set(terminals)<=reached:fail(f"Disconnected net {net['name']} in {view}")
                    net_groups.append((net["name"],reached))
                for i,(name,group) in enumerate(net_groups):
                    for other,othergroup in net_groups[i+1:]:
                        if group&othergroup:fail(f"Shorted nets {name}/{other} in {view}")
                layout=manifest["layout"][view];rules=dict(layout["rules"]);rules.pop("grid",None)
                errors.extend(f"{view}: {e}" for e in validate_geometry(layout["pins"],layout["segments"],**rules))
            # The hash manifest is not allowed to become an alternative source of geometry.
            # Regenerate canonical XML from declared intent and saved layout to catch edits
            # to actual instance positions/connectors, even if member hashes were updated.
            canonical=project_xml(manifest["design"],manifest["modules"],manifest["layout"])
            if ET.tostring(ET.fromstring(canonical))!=ET.tostring(root):fail("Native XML differs from declared geometry/connectivity")
    except (ValueError,KeyError,TypeError,AttributeError,IndexError,zipfile.BadZipFile,ET.ParseError,StopIteration) as exc:
        fail(str(exc))
    return {"passed":not errors,"errors":errors,"checks":["archive and SVG connector integrity","saved reciprocal electrical connectivity in three views","net continuity and cross-net shorts","component placement during generation","geometric trace/pad/edge clearances"],"native_fritzing_drc":"not_run","scope":"Workbench schema v1, single-layer through-hole board; not general ERC or manufacturer approval"}


def validate(path):return validate_archive_bytes(Path(path).read_bytes())
