package dev.violence.game;

import dev.violence.ViolencePlugin;
import dev.violence.arena.Arena;
import dev.violence.fx.Glyphs;
import dev.violence.logic.ComboTracker;
import dev.violence.logic.KillType;
import dev.violence.math.Vec3;
import dev.violence.player.PlayerCombatant;
import net.kyori.adventure.text.Component;

/**
 * 점수: 처치 방식별 점수(어려울수록 높음) + 10초 콤보 보너스.
 * Skript 가 있으면 Skript 가 점수를 계산해 /violence award 로 돌려준다.
 */
public final class ScoreService {
    private final ViolencePlugin plugin;
    private final SkriptBridge bridge;
    /** Skript 응답 대기 중인 처치 (동기 호출 중에만 유효) */
    private PlayerCombatant pendingKiller;
    private Vec3 pendingPos;
    private boolean pendingAnswered;
    private PlayerCombatant pendingComboPlayer;
    private boolean pendingComboAnswered;

    public ScoreService(ViolencePlugin plugin, SkriptBridge bridge) {
        this.plugin = plugin;
        this.bridge = bridge;
    }

    public int defaultPoints(KillType type, boolean headshot) {
        int base = plugin.getConfig().getInt("score.kill." + type.name().toLowerCase(), type.defaultPoints());
        if (headshot) base += plugin.getConfig().getInt("score.headshot-bonus", 50);
        return base;
    }

    public long comboWindow(PlayerCombatant pc) {
        long w = plugin.getConfig().getLong("score.combo-seconds", 10) * 20;
        if (pc.mask == dev.violence.mask.Mask.ZACK) w = (long) (w * 1.6);
        return w;
    }

    /** 플레이어가 처치함 */
    public void onPlayerKill(PlayerCombatant killer, KillType type, boolean headshot, Vec3 at, String victimName) {
        pendingKiller = killer;
        pendingPos = at;
        pendingAnswered = false;
        bridge.call("kill", killer.name(), victimName, type.name(), headshot, killer.combo.count() + 1);
        if (!pendingAnswered) award(killer, defaultPoints(type, headshot), at);
        pendingKiller = null;
    }

    /** Skript 또는 기본값으로 점수 지급 + 팝업 + 콤보 갱신 */
    public void award(PlayerCombatant pc, int points, Vec3 at) {
        if (pc == pendingKiller) pendingAnswered = true;
        Vec3 pos = at != null ? at : pendingPos;
        long now = plugin.now();
        pc.score += points;
        int count = pc.combo.registerKill(now, points, comboWindow(pc));
        Arena a = plugin.arena();
        if (a != null && pos != null) {
            Component text = Component.empty()
                    .append(Glyphs.text("+" + points, Glyphs.POPUP, count >= 2 ? Glyphs.YELLOW : Glyphs.WHITE));
            plugin.hud().popup(a, pc.player(), pos.add(0, 1.9, 0), text);
        }
    }

    /** Skript 에서 /violence award <플레이어> <점수> */
    public void awardFromSkript(PlayerCombatant pc, int points) {
        award(pc, points, pc == pendingKiller ? pendingPos : pc.feet());
    }

    public void tick(long now) {
        Arena a = plugin.arena();
        if (a == null) return;
        for (PlayerCombatant pc : a.players.values()) {
            ComboTracker.ComboEnd end = pc.combo.tick(now);
            if (end != null) finishCombo(pc, end);
        }
    }

    public void finishCombo(PlayerCombatant pc, ComboTracker.ComboEnd end) {
        if (end.count() < 2) return;
        pendingComboPlayer = pc;
        pendingComboAnswered = false;
        bridge.call("comboend", pc.name(), end.count(), end.basePoints());
        if (!pendingComboAnswered) comboBonus(pc, ComboTracker.defaultBonus(end.count(), end.basePoints()));
        pendingComboPlayer = null;
    }

    public void comboBonus(PlayerCombatant pc, int bonus) {
        if (pc == pendingComboPlayer) pendingComboAnswered = true;
        if (bonus <= 0) return;
        pc.score += bonus;
        plugin.hud().comboScore(pc.player(), bonus, plugin.now());
        plugin.fx().sound(pc.world(), pc.eye(), "violence:ui.combo_end", 0.9f, 1f);
    }

    /** 죽으면 진행 중이던 콤보를 즉시 정산 */
    public void flushCombo(PlayerCombatant pc) {
        if (pc.combo.count() == 0) return;
        ComboTracker.ComboEnd end = new ComboTracker.ComboEnd(pc.combo.count(), pc.combo.basePoints());
        pc.combo.clear();
        finishCombo(pc, end);
    }
}
