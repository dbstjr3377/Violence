package dev.violence.mapgen;

/** XZ 평면 사각형 (양 끝 포함). */
public record Rect(int x1, int z1, int x2, int z2) {
    public Rect {
        if (x1 > x2) { int t = x1; x1 = x2; x2 = t; }
        if (z1 > z2) { int t = z1; z1 = z2; z2 = t; }
    }

    public int width() { return x2 - x1 + 1; }
    public int depth() { return z2 - z1 + 1; }
    public int area() { return width() * depth(); }
    public int cx() { return (x1 + x2) / 2; }
    public int cz() { return (z1 + z2) / 2; }

    public Rect shrink(int n) { return new Rect(x1 + n, z1 + n, x2 - n, z2 - n); }

    public boolean contains(int x, int z) { return x >= x1 && x <= x2 && z >= z1 && z <= z2; }
}
