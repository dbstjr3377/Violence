package dev.violence.mapgen;

import dev.violence.arena.GameMap;
import java.util.Random;

/** 내장 맵 생성기. 월드에 블록을 직접 배치하고 맵 데이터(문, 무기, 리스폰 위치)를 돌려준다. */
public interface MapGenerator {
    String id();

    String displayName();

    GameMap generate(BlockAccess world, Random rnd);
}
