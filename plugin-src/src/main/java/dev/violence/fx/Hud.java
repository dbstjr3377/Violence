package dev.violence.fx;

import dev.violence.ViolencePlugin;
import dev.violence.arena.Arena;
import dev.violence.math.Vec3;
import java.time.Duration;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import net.kyori.adventure.bossbar.BossBar;
import net.kyori.adventure.text.Component;
import net.kyori.adventure.title.Title;
import org.bukkit.Color;
import org.bukkit.entity.Display;
import org.bukkit.entity.Player;
import org.bukkit.entity.TextDisplay;
import org.bukkit.util.Transformation;
import org.joml.Quaternionf;
import org.joml.Vector3f;

/**
 * 화면 표시 (커스텀 폰트 사용).
 * - 액션바: 무기 이름 / 남은 탄수 / 처형 안내
 * - 보스바 1: 남은 시간, 목표 킬, 1위
 * - 보스바 2: 콤보 (좌상단)
 * - 보스바 3: 콤보 점수 (콤보 바로 아래, 왼쪽에서 슬라이드)
 * - 제목: 가면 착용 안내(화면 중앙 하단), 검은 화면 페이드
 * - 텍스트 디스플레이: 처치 점수 팝업 (죽인 사람에게만 보임)
 * 보스바 게이지는 리소스팩에서 투명 처리된다.
 */
public final class Hud {
    /** 콤보 표시를 화면 중앙에서 왼쪽으로 미는 거리 (GUI 픽셀) */
    public static final int LEFT_SHIFT = 150;

    private static final class PlayerHud {
        BossBar status;
        BossBar combo;
        BossBar comboScore;
        Component lastAction = Component.empty();
        long lastActionTick = -100;
        int slidePoints;
        long slideStart = -1000;
    }

    private final ViolencePlugin plugin;
    private final Map<UUID, PlayerHud> huds = new HashMap<>();

    public Hud(ViolencePlugin plugin) {
        this.plugin = plugin;
    }

    private PlayerHud hud(Player p) {
        return huds.computeIfAbsent(p.getUniqueId(), k -> {
            PlayerHud h = new PlayerHud();
            h.status = BossBar.bossBar(Component.empty(), 0f, BossBar.Color.WHITE, BossBar.Overlay.PROGRESS);
            h.combo = BossBar.bossBar(Component.empty(), 0f, BossBar.Color.WHITE, BossBar.Overlay.PROGRESS);
            h.comboScore = BossBar.bossBar(Component.empty(), 0f, BossBar.Color.WHITE, BossBar.Overlay.PROGRESS);
            p.showBossBar(h.status);
            p.showBossBar(h.combo);
            p.showBossBar(h.comboScore);
            return h;
        });
    }

    /** 가운데 정렬되는 보스바 텍스트를 왼쪽으로 밀기: 오른쪽에 2배 공백을 붙인다 */
    private static Component shiftedLeft(Component content, int shift) {
        return Component.empty().append(content).append(Glyphs.space(shift * 2));
    }

    public void status(Player p, Component text) {
        hud(p).status.name(text);
    }

    /** 콤보 표시. count < 2 면 숨김. */
    public void combo(Player p, int count, double remaining) {
        PlayerHud h = hud(p);
        if (count < 2) {
            h.combo.name(Component.empty());
            return;
        }
        int bars = (int) Math.round(remaining * 10);
        Component c = Component.empty()
                .append(Glyphs.text(count + "x", Glyphs.COMBO, Glyphs.YELLOW))
                .append(Glyphs.text(" COMBO ", Glyphs.COMBO, Glyphs.PINK))
                .append(Glyphs.text("▮".repeat(bars), Glyphs.HUD, Glyphs.YELLOW))
                .append(Glyphs.text("▮".repeat(10 - bars), Glyphs.HUD, 0x553344));
        h.combo.name(shiftedLeft(c, LEFT_SHIFT));
    }

    /** 콤보 종료 점수: 왼쪽에서 부드럽게 나와 0.8초 표시 */
    public void comboScore(Player p, int points, long now) {
        PlayerHud h = hud(p);
        h.slidePoints = points;
        h.slideStart = now;
    }

    public void action(Player p, Component text, long now) {
        PlayerHud h = hud(p);
        // 같은 내용이면 1.5초마다만 다시 보냄 (액션바가 사라지지 않게)
        if (!text.equals(h.lastAction) || now - h.lastActionTick > 30) {
            p.sendActionBar(text);
            h.lastAction = text;
            h.lastActionTick = now;
        }
    }

    /** 매 틱: 슬라이드 애니메이션 */
    public void tick(Player p, long now) {
        PlayerHud h = huds.get(p.getUniqueId());
        if (h == null) return;
        long age = now - h.slideStart;
        if (age >= 0 && age <= 16 + 6) {
            // 0~6틱: 왼쪽에서 들어옴(ease-out), 16틱(0.8초) 표시 후 사라짐
            double t = Math.min(1.0, age / 6.0);
            double ease = 1 - Math.pow(1 - t, 3);
            int extra = (int) Math.round((1 - ease) * 120);
            if (age > 16) {
                h.comboScore.name(Component.empty());
                h.slideStart = -1000;
            } else {
                Component c = Glyphs.text("+" + String.format("%,d", h.slidePoints), Glyphs.COMBO, Glyphs.CYAN);
                h.comboScore.name(shiftedLeft(c, LEFT_SHIFT + extra));
            }
        }
    }

    /** 화면 중앙 하단 안내 (1초간 표시 후 자연스럽게 사라짐) */
    public void prompt(Player p, String text) {
        Title t = Title.title(Component.empty(), Glyphs.text(text, Glyphs.PROMPT, Glyphs.WHITE),
                Title.Times.times(Duration.ofMillis(150), Duration.ofMillis(850), Duration.ofMillis(400)));
        p.showTitle(t);
    }

    /** 검은 단색 화면 페이드 */
    public void fadeBlack(Player p, int inTicks, int stayTicks, int outTicks) {
        Title t = Title.title(Glyphs.text(Glyphs.BLACK_SCREEN, Glyphs.OVERLAY, 0xFFFFFF), Component.empty(),
                Title.Times.times(Duration.ofMillis(inTicks * 50L), Duration.ofMillis(stayTicks * 50L), Duration.ofMillis(outTicks * 50L)));
        p.showTitle(t);
    }

    /** 처치 점수 팝업: 사망한 개체 위에 0.8초간, 죽인 사람에게만 보임 */
    public void popup(Arena a, Player viewer, Vec3 at, Component text) {
        TextDisplay d = a.track(a.world.spawn(Fx.loc(a.world, at), TextDisplay.class, td -> {
            td.text(text);
            td.setBillboard(Display.Billboard.CENTER);
            td.setBackgroundColor(Color.fromARGB(0, 0, 0, 0));
            td.setShadowed(true);
            td.setSeeThrough(true);
            td.setPersistent(false);
            td.setVisibleByDefault(false);
            td.setBrightness(new Display.Brightness(15, 15));
            td.setTransformation(new Transformation(new Vector3f(), new Quaternionf(), new Vector3f(0.4f, 0.4f, 0.4f), new Quaternionf()));
        }));
        viewer.showEntity(plugin, d);
        plugin.later(1, () -> {
            if (!d.isValid()) return;
            d.setInterpolationDelay(0);
            d.setInterpolationDuration(4);
            d.setTransformation(new Transformation(new Vector3f(0, 0.25f, 0), new Quaternionf(), new Vector3f(1.25f, 1.25f, 1.25f), new Quaternionf()));
        });
        plugin.later(6, () -> {
            if (!d.isValid()) return;
            d.setInterpolationDelay(0);
            d.setInterpolationDuration(10);
            d.setTransformation(new Transformation(new Vector3f(0, 0.6f, 0), new Quaternionf(), new Vector3f(1.0f, 1.0f, 1.0f), new Quaternionf()));
        });
        plugin.later(16, () -> {
            a.tracked.remove(d);
            if (d.isValid()) d.remove();
        });
    }

    public void clear(Player p) {
        PlayerHud h = huds.remove(p.getUniqueId());
        if (h != null) {
            p.hideBossBar(h.status);
            p.hideBossBar(h.combo);
            p.hideBossBar(h.comboScore);
        }
        p.sendActionBar(Component.empty());
        p.clearTitle();
    }
}
