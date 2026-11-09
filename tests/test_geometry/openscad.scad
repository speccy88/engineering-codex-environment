// Parametric plate: millimeters, watertight constructive solid geometry.
width = 40;
depth = 25;
height = 3;
hole_diameter = 4;
$fn = 96;
difference() {
    cube([width, depth, height]);
    for (x = [10, 30])
        translate([x, 12.5, -1]) cylinder(h=height+2, d=hole_diameter);
}
