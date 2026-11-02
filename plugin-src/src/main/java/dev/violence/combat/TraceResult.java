package dev.violence.combat;

import dev.violence.arena.Door;
import dev.violence.math.Hitbox;
import dev.violence.math.Vec3;
import java.util.ArrayList;
import java.util.List;

/** 히트스캔 한 발의 결과. */
public final class TraceResult {
    public record EntityHit(Combatant target, Hitbox.Part part, double distance, Vec3 point) {}

    public Vec3 end;
    /** 벽에 박힌 경우 그 면의 법선 (혈흔/탄흔 방향), 없으면 null */
    public Vec3 wallNormal;
    public Door door;
    public final List<EntityHit> hits = new ArrayList<>();
    public final List<Vec3> brokenGlass = new ArrayList<>();
}
