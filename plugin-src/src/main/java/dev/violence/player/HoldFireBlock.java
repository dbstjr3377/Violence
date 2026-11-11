package dev.violence.player;

import org.bukkit.Location;
import org.bukkit.Material;
import org.bukkit.World;
import org.bukkit.block.data.BlockData;
import org.bukkit.entity.LivingEntity;
import org.bukkit.entity.Player;
import org.bukkit.util.RayTraceResult;
import org.bukkit.util.Vector;

/**
 * 연사 무기를 적에게 겨눈 채 꾹 누르기.
 *
 * 서버는 "왼클릭을 누르고 있음"을 클라이언트가 블록을 겨누고 누를 때 매 틱 보내는 휘두르기 패킷으로만 안다.
 * 그런데 조준점에 인물(NPC·플레이어·시체)이 걸리면 클라이언트가 블록 대신 "아무것도 안 겨눔"으로 처리해
 * 휘두르기를 한 번만 보내고 끝나므로, 적을 겨누면 연사가 한 발로 끝났다.
 *
 * 그래서 연사 무기를 든 플레이어에게만, 조준선이 인물에 닿는 칸에 보이지 않는 가짜 블록(가루눈)을 보낸다.
 * 클라이언트는 그 블록을 겨누고 있다고 여겨 누르는 동안 매 틱 휘두르기를 보내고, 실제 사격 판정은 서버가 따로 한다.
 * 가루눈은 플레이어와 부딪히지 않고, 리소스팩에서 모양·입자·소리를 모두 지웠다 (블록 테두리도 쉐이더에서 안 그림).
 */
public final class HoldFireBlock {
    private static final BlockData FAKE = Material.POWDER_SNOW.createBlockData();
    private static final double RANGE = 64;

    private Location shown;

    /** 매 틱: active = 연사 무기를 들고 움직일 수 있는 상태 */
    public void tick(Player p, boolean active) {
        Location want = active ? target(p) : null;
        if (shown != null && (want == null || !sameBlock(shown, want))) {
            if (p.isOnline() && shown.getWorld() == p.getWorld()) p.sendBlockChange(shown, shown.getBlock().getBlockData());
            shown = null;
        }
        if (want != null) {
            // 서버가 그 칸을 다시 보내 지워질 수 있으므로 매 틱 다시 보냄
            p.sendBlockChange(want, FAKE);
            shown = want;
        }
    }

    public void clear(Player p) {
        tick(p, false);
    }

    /** 조준선이 블록보다 먼저 인물에 닿으면, 닿기 직전 칸 (빈 칸만) */
    private static Location target(Player p) {
        Location eye = p.getEyeLocation();
        Vector dir = eye.getDirection();
        World w = p.getWorld();
        RayTraceResult block = w.rayTraceBlocks(eye, dir, RANGE, org.bukkit.FluidCollisionMode.NEVER, false);
        double maxDist = block == null ? RANGE : block.getHitPosition().distance(eye.toVector());
        RayTraceResult ent = w.rayTraceEntities(eye, dir, maxDist, 0.0,
                e -> e != p && e instanceof LivingEntity && !(e instanceof Player q && q.getGameMode() == org.bukkit.GameMode.SPECTATOR));
        if (ent == null) return null;
        double d = ent.getHitPosition().distance(eye.toVector());
        if (d < 1.3) return null;
        Vector at = eye.toVector().add(dir.clone().multiply(d - 0.05));
        Location l = new Location(w, Math.floor(at.getX()), Math.floor(at.getY()), Math.floor(at.getZ()));
        if (!l.getBlock().getType().isAir()) return null;
        // 내 몸이 있는 칸은 피함
        Location feet = p.getLocation();
        if (l.getBlockX() == feet.getBlockX() && l.getBlockZ() == feet.getBlockZ()
                && l.getBlockY() >= feet.getBlockY() - 1 && l.getBlockY() <= feet.getBlockY() + 2) return null;
        return l;
    }

    private static boolean sameBlock(Location a, Location b) {
        return a.getWorld() == b.getWorld() && a.getBlockX() == b.getBlockX() && a.getBlockY() == b.getBlockY() && a.getBlockZ() == b.getBlockZ();
    }
}
