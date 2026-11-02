package dev.violence.fx;

import io.papermc.paper.math.Angle;
import java.util.HashMap;
import java.util.Map;
import java.util.Random;
import java.util.UUID;
import org.bukkit.entity.Player;

/**
 * 화면 흔들림. 서버가 플레이어의 시야를 상대 각도로 살짝 돌렸다가 되돌린다.
 * 매 틱 "새 오프셋 - 이전 오프셋" 만큼만 회전시키므로 조준이 누적해서 밀리지 않는다.
 */
public final class Shake {
    private static final class State {
        double trauma;
        double baseline;
        double lastYaw;
        double lastPitch;
        double recoilPitch;
        long t;
    }

    private final Map<UUID, State> states = new HashMap<>();
    private final Random rnd = new Random();

    private State st(Player p) {
        return states.computeIfAbsent(p.getUniqueId(), k -> new State());
    }

    /** 순간 흔들림. amount 0..1 (총 발사 0.15, 처형 0.6 등) */
    public void add(Player p, double amount) {
        State s = st(p);
        s.trauma = Math.min(1.0, s.trauma + amount);
    }

    /** 흔들림을 최소 amount 로 유지 (연사 잔떨림) */
    public void atLeast(Player p, double amount) {
        State s = st(p);
        s.trauma = Math.max(s.trauma, Math.min(1.0, amount));
    }

    /** 총기 반동: 위로 살짝 튀었다가 돌아옴 */
    public void recoil(Player p, double degrees) {
        st(p).recoilPitch += degrees;
    }

    /** 연속킬 효과 등 지속적인 흔들림 기준치 */
    public void setBaseline(Player p, double baseline) {
        st(p).baseline = baseline;
    }

    public void tick(Iterable<Player> players) {
        for (Player p : players) {
            State s = states.get(p.getUniqueId());
            if (s == null) continue;
            s.t++;
            double level = Math.max(s.trauma, s.baseline);
            double mag = level * level;
            double yaw = 0, pitch = 0;
            if (mag > 0.0005) {
                // 큰 흔들림은 무작위, 지속 흔들림은 부드러운 사인파
                double noiseYaw = (rnd.nextDouble() * 2 - 1) * s.trauma * s.trauma;
                double noisePitch = (rnd.nextDouble() * 2 - 1) * s.trauma * s.trauma;
                double wave = s.baseline * s.baseline;
                yaw = (noiseYaw * 5.0) + Math.sin(s.t * 0.37) * wave * 2.2;
                pitch = (noisePitch * 3.5) + Math.sin(s.t * 0.53 + 1.3) * wave * 1.6;
            }
            pitch -= s.recoilPitch;
            s.recoilPitch *= 0.55;
            if (Math.abs(s.recoilPitch) < 0.02) s.recoilPitch = 0;
            double dy = yaw - s.lastYaw;
            double dp = pitch - s.lastPitch;
            if (Math.abs(dy) > 0.001 || Math.abs(dp) > 0.001) {
                p.setRotation(Angle.relative((float) dy), Angle.relative((float) dp));
            }
            s.lastYaw = yaw;
            s.lastPitch = pitch;
            s.trauma = Math.max(0, s.trauma - 0.06);
        }
    }

    public void remove(Player p) {
        states.remove(p.getUniqueId());
    }

    public void reset(Player p) {
        State s = states.get(p.getUniqueId());
        if (s != null) {
            s.trauma = 0;
            s.baseline = 0;
            s.recoilPitch = 0;
        }
    }
}
