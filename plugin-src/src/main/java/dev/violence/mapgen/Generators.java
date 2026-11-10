package dev.violence.mapgen;

import java.util.List;

/** 내장 맵 목록. */
public final class Generators {
    private static final List<MapGenerator> ALL = List.of(
            new ApartmentA(), new ApartmentB(), new BuildingA(), new BuildingB(),
            new Prison(), new Sewer(), new Restaurant(), new Club());

    /** 생성기 버전: 팔레트·구조를 바꾸면 올림 → 저장된 내장 맵을 새로 생성 (2 = 이 게임 전용 재질 팔레트) */
    public static final int VERSION = 2;

    private Generators() {}

    public static List<MapGenerator> all() { return ALL; }

    public static MapGenerator get(String id) {
        for (MapGenerator g : ALL) if (g.id().equalsIgnoreCase(id)) return g;
        return null;
    }
}
