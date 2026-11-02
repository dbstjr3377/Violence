package dev.violence.mapgen;

/**
 * 맵 생성기가 블록을 읽고 쓰는 통로. 블록은 "minecraft:stone_slab[type=top]" 같은 상태 문자열로 다룬다.
 * 실제 서버에서는 월드에, 테스트에서는 메모리 지도에 연결된다.
 */
public interface BlockAccess {
    void set(int x, int y, int z, String state);

    /** 블록 상태 문자열, 공기면 null */
    String get(int x, int y, int z);

    default boolean isAir(int x, int y, int z) {
        String s = get(x, y, z);
        return s == null || s.startsWith("minecraft:air") || s.startsWith("minecraft:cave_air");
    }
}
