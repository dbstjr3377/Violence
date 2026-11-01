package dev.violence.fx;

import dev.violence.math.Vec3;

/**
 * 클럽 맵 조명 공식. 리소스팩 쉐이더 tools/shaders/include/violence_club.glsl 과 같은 상수/공식을 쓴다.
 * 쉐이더는 블록 표면의 빛(원뿔 자국, 미러볼 점, 레이저 선)을 그리고,
 * 플러그인은 같은 시각의 같은 방향으로 공중에 보이는 빛줄기 엔티티를 움직인다.
 * 시간은 월드 게임 시간(틱) 기준: 초 = (gameTime % 24000) / 20.
 */
public final class ClubLights {
    private ClubLights() {}

    /** 클럽 1층 바닥 블록 y. 쉐이더는 카메라가 이 높이 대역에 있을 때만 켜진다. */
    public static final int Y0 = 192;
    public static final double BPM = 128.0;
    public static final int SPOTS = 6;
    public static final int LASERS = 3;
    public static final int LASER_BEAMS = 5;
    public static final double SPOT_Y = 201.6;
    public static final Vec3 LASER = new Vec3(0.5, 196.0, -12.5);
    public static final Vec3 BALL = new Vec3(0.5, 200.5, 0.5);
    /** 무빙 라이트 원뿔 바깥 반각 (쉐이더 smoothstep 의 cos 0.975) */
    public static final double SPOT_HALF_ANGLE = Math.acos(0.975);
    public static final String[] COLORS = {"magenta", "cyan", "violet", "orange", "green"};
    private static final double TAU = Math.PI * 2;

    public static double seconds(long gameTime) {
        return Math.floorMod(gameTime, 24000L) / 20.0;
    }

    public static double beat(double s) {
        return s * BPM / 60.0;
    }

    public static Vec3 spotPos(int i) {
        return new Vec3(-14.5 + 6.0 * i, SPOT_Y, i % 2 == 0 ? -5.5 : 6.5);
    }

    public static Vec3 spotDir(int i, double s) {
        double pan = i * 1.7 + 1.1 * Math.sin(TAU * 48.0 / 1200.0 * s + i * 1.3);
        double tilt = 0.55 + 0.35 * Math.sin(TAU * 70.0 / 1200.0 * s + i * 2.1);
        return new Vec3(Math.sin(tilt) * Math.cos(pan), -Math.cos(tilt), Math.sin(tilt) * Math.sin(pan));
    }

    /** 색 번호 (COLORS 순서). 8박자마다 바뀐다. */
    public static int spotColor(int i, double s) {
        return Math.floorMod(i + (int) Math.floor(beat(s) / 8.0), COLORS.length);
    }

    /** 레이저는 16박자마다 켜졌다 꺼졌다 한다 */
    public static boolean lasersOn(double s) {
        return ((int) Math.floor(beat(s) / 16.0)) % 2 == 1;
    }

    public static Vec3 laserNormal(int j, double s) {
        double tilt = -0.18 + 0.16 * Math.sin(TAU * 90.0 / 1200.0 * s + j * 2.0) + 0.12 * (j - 1.0);
        double yaw = 0.45 * Math.sin(TAU * 40.0 / 1200.0 * s + j * 1.7);
        double nx = 0, ny = Math.cos(tilt), nz = -Math.sin(tilt);
        return new Vec3(nx * Math.cos(yaw) + nz * Math.sin(yaw), ny, -nx * Math.sin(yaw) + nz * Math.cos(yaw));
    }

    /** 레이저 판 j 안에서 부채꼴로 퍼지는 k번째 빛줄기 방향 (판 위에 있으므로 쉐이더가 그린 선과 만난다) */
    public static Vec3 laserBeam(int j, int k, double s) {
        Vec3 n = laserNormal(j, s);
        Vec3 fwd = new Vec3(0, 0, 1);
        Vec3 f = fwd.sub(n.mul(fwd.dot(n))).normalize();
        Vec3 side = n.cross(f).normalize();
        double a = -0.6 + 1.2 * k / (LASER_BEAMS - 1);
        return f.mul(Math.cos(a)).add(side.mul(Math.sin(a)));
    }

    /** 레이저 색: 가운데 판은 빨강, 나머지는 초록 */
    public static String laserColor(int j) {
        return j == 1 ? "red" : "green";
    }

    /** 미러볼 회전각 (라디안) */
    public static double ballAngle(double s) {
        return TAU * 30.0 / 1200.0 * s;
    }
}
