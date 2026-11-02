package dev.violence.mapgen;

import java.util.List;

/** 내장 맵 목록. */
public final class Generators {
    private static final List<MapGenerator> ALL = List.of(
            new ApartmentA(), new ApartmentB(), new BuildingA(), new BuildingB(),
            new Prison(), new Sewer(), new Restaurant(), new Club());

    private Generators() {}

    public static List<MapGenerator> all() { return ALL; }

    public static MapGenerator get(String id) {
        for (MapGenerator g : ALL) if (g.id().equalsIgnoreCase(id)) return g;
        return null;
    }
}
