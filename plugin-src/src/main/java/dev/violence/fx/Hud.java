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
    /** 상단(보스바) 글을 모두 숨김: 시간·목표·1위·점수·콤보·콤보 점수 */
    private static final boolean HIDE_TOP = true;

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
            // 상태 보스바는 늘 "화면 어둡게" 표시 → 클라이언트의 어둡게 값이 1 로 유지 (처치 깜빡임의 시계, 아래 killFlash)
            h.status = BossBar.bossBar(Component.empty(), 0f, BossBar.Color.WHITE, BossBar.Overlay.PROGRESS, java.util.Set.of(BossBar.Flag.DARKEN_SCREEN));
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

    /** 상단 글은 띄우지 않음 (보스바는 처치 깜빡임 신호용으로만 남김) */
    public void status(Player p, Component text) {
        hud(p);
    }

    /** 콤보 표시. count < 2 면 숨김. */
    public void combo(Player p, int count, double remaining) {
        PlayerHud h = hud(p);
        if (HIDE_TOP) {
            h.combo.name(Component.empty());
            return;
        }
        if (count < 2) {
            h.combo.name(Component.empty());
            return;
        }
        int bars = (int) Math.round(remaining * 10);
        Component c = Component.empty()
                .append(Glyphs.text(count + "x", Glyphs.COMBO, Glyphs.YELLOW))
                .append(Glyphs.text(" COMBO ", Glyphs.COMBO, Glyphs.PINK))
                .append(Glyphs.text(Glyphs.BAR.repeat(bars), Glyphs.HUD, Glyphs.YELLOW))
                .append(Glyphs.text(Glyphs.BAR.repeat(10 - bars), Glyphs.HUD, 0x553344));
        h.combo.name(shiftedLeft(c, LEFT_SHIFT));
    }

    /** 콤보 종료 점수: 왼쪽에서 부드럽게 나와 0.8초 표시 */
    public void comboScore(Player p, int points, long now) {
        if (HIDE_TOP) return;
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

    /** 총으로 맞힘: 조준점에 짧은 히트마커 (처치면 빨강) */
    public void hitmarker(Player p, boolean kill) {
        Title t = Title.title(Glyphs.text(kill ? Glyphs.HITMARKER_KILL : Glyphs.HITMARKER, Glyphs.OVERLAY, 0xFFFFFF), Component.empty(),
                Title.Times.times(Duration.ZERO, Duration.ofMillis(kill ? 200 : 100), Duration.ofMillis(150)));
        p.showTitle(t);
    }

    /** 처치 회색 깜빡임 길이 (틱) */
    public static final int FLASH_TICKS = 27;   // 0.75배 속도 (쉐이더 violence_flash.glsl 과 같이)

    /** 깜빡임 상태: dropAt = "화면 어둡게"를 끈 틱(시계 0), end = 끝나는 틱, rising = 되감는 중 */
    private static final class Flash {
        long dropAt;
        long end;
        boolean rising;
        long token;
    }

    private final Map<UUID, Flash> flashes = new HashMap<>();
    private long flashSeq;

    /** 클라이언트가 "화면 어둡게" 값을 바꾸는 빠르기 (틱당): 켜면 +0.05, 끄면 -0.0125 */
    static final double DARKEN_UP = 0.05;
    static final double DARKEN_DOWN = 0.0125;

    /** 깜빡임 도중 다시 처치: 지난 틱 수만큼 내려간 값을 되돌리는 데 걸리는 틱 (그동안 화면이 다시 흑백으로 차오름) */
    static int rewindTicks(long elapsed) {
        double down = Math.min(1.0, Math.max(0, elapsed) * DARKEN_DOWN);
        return (int) Math.ceil(down / DARKEN_UP - 1e-9);
    }

    /**
     * 처치: 화면이 흑백으로 번쩍였다가 easeOutCirc 로 원래 색으로 돌아옴 (쉐이더, 상태이상 효과 없음).
     * 보이지 않는 HUD 보스바의 플래그만 바꿔서 쉐이더에 신호를 준다 (리소스팩 violence_flash.glsl / lightmap.fsh):
     *  - 평소: 상태 보스바에 "화면 어둡게" → 클라이언트 값이 1 (리소스팩 라이트맵 쉐이더가 바닐라의 어둡게 하기를 지움)
     *  - 처치: "화면 어둡게"를 끄면 클라이언트가 그 값을 틱당 1/80 씩 부드럽게(프레임 보간) 줄임 → 쉐이더의 시계
     *          동시에 콤보 보스바에 "안개" 플래그 → 쉐이더가 안개 거리로 "깜빡임 중"을 알아챔
     *  - FLASH_TICKS 뒤: 둘 다 원래대로
     * 깜빡임 도중에 또 처치하면 (연속 킬, 붉은 연속킬 화면 중에도) 씹히지 않고 다시 깜빡인다:
     * "화면 어둡게"를 잠깐 다시 켜서 값을 1 로 되돌리면(그동안 흑백이 다시 차오름) 그때부터 시계가 처음부터 다시 간다.
     */
    public void killFlash(Player p) {
        PlayerHud h = hud(p);
        long now = plugin.now();
        Flash f = flashes.get(p.getUniqueId());
        if (f != null && now < f.end) {
            if (f.rising) return;   // 이미 되감는 중 → 곧 처음부터 다시 감
            int rise = rewindTicks(now - f.dropAt);
            if (rise <= 0) return;
            long token = ++flashSeq;
            f.token = token;
            f.rising = true;
            f.end = now + rise + FLASH_TICKS;
            h.status.addFlag(BossBar.Flag.DARKEN_SCREEN);
            plugin.later(rise, () -> {
                if (f.token != token || flashes.get(p.getUniqueId()) != f) return;
                f.rising = false;
                f.dropAt = plugin.now();
                h.status.removeFlag(BossBar.Flag.DARKEN_SCREEN);
                scheduleFlashEnd(p, h, f, token, FLASH_TICKS);
            });
            return;
        }
        Flash nf = new Flash();
        nf.token = ++flashSeq;
        nf.dropAt = now;
        nf.end = now + FLASH_TICKS;
        flashes.put(p.getUniqueId(), nf);
        h.status.removeFlag(BossBar.Flag.DARKEN_SCREEN);
        h.combo.addFlag(BossBar.Flag.CREATE_WORLD_FOG);
        scheduleFlashEnd(p, h, nf, nf.token, FLASH_TICKS);
    }

    private void scheduleFlashEnd(Player p, PlayerHud h, Flash f, long token, int ticks) {
        plugin.later(ticks, () -> {
            if (f.token != token || flashes.get(p.getUniqueId()) != f) return;
            flashes.remove(p.getUniqueId());
            h.combo.removeFlag(BossBar.Flag.CREATE_WORLD_FOG);
            h.status.addFlag(BossBar.Flag.DARKEN_SCREEN);
        });
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

    /** 접속 종료: 이전 연결에 보였던 보스바 캐시 제거 (재접속 시 새로 만들도록) */
    public void forget(java.util.UUID id) {
        huds.remove(id);
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
