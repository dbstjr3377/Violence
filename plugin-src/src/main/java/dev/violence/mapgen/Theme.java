package dev.violence.mapgen;

/** 맵 분위기별 블록 팔레트 (블록 상태 문자열). */
public final class Theme {
    public String wall, wallAccent, floor, floorAlt, ceiling, light, glass, table, counter, trim, outside;

    public static Theme of(String wall, String accent, String floor, String floorAlt, String ceiling, String light,
                           String glass, String table, String counter, String trim, String outside) {
        Theme t = new Theme();
        t.wall = wall;
        t.wallAccent = accent;
        t.floor = floor;
        t.floorAlt = floorAlt;
        t.ceiling = ceiling;
        t.light = light;
        t.glass = glass;
        t.table = table;
        t.counter = counter;
        t.trim = trim;
        t.outside = outside;
        return t;
    }

    /** 블록 이름만 (상태 제외, 네임스페이스 제외) */
    public static String name(String state) {
        if (state == null) return "air";
        String s = state.startsWith("minecraft:") ? state.substring(10) : state;
        int i = s.indexOf('[');
        return i >= 0 ? s.substring(0, i) : s;
    }
}
