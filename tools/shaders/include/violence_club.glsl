#ifndef VIOLENCE_CLUB_GLSL
#define VIOLENCE_CLUB_GLSL

// ───────────────────────── VIOLENCE: 클럽 맵 전용 조명 ─────────────────────────
// 카메라가 클럽 구역(높은 y 대역)에 있을 때만 블록 표면에 클럽 조명을 입힌다.
//  - 천장 무빙 라이트 6개: 색 원뿔이 바닥과 벽을 쓸고 다님 (8박자마다 색 변경)
//  - 미러볼: 홀 전체에 회전하는 빛 점
//  - 레이저: DJ 부스에서 나오는 빛의 판이 벽/바닥에 선을 그림 (16박자마다 켜짐/꺼짐)
//  - LED 댄스 플로어: 2x2 타일이 박자에 맞춰 색이 바뀌고 번쩍임
//  - 128 BPM 킥에 맞춘 홀 전체 색 펄스, 32박자마다 약한 스트로브 두 번
// 상수와 공식은 플러그인 dev.violence.fx.ClubLights 와 같아야 한다 (공중 빛줄기 엔티티와 동기화).
// 시간: GameTime(0..1, 24000틱 주기) × 1200 = 초. 모든 주기를 1200초의 약수로 맞춰 넘어갈 때 끊기지 않게 함.

const float CLUB_Y0 = 192.0;                 // 1층 바닥 블록 y (윗면은 +1)
const float CLUB_BPM = 128.0;
const float CLUB_TAU = 6.28318530718;
const vec3 CLUB_MIN = vec3(-37.0, 190.0, -31.0);   // 클럽 건물 전체
const vec3 CLUB_MAX = vec3(38.0, 215.0, 32.0);
const vec3 CLUB_HALL_MIN = vec3(-21.0, 192.0, -15.0); // 2층 높이 댄스홀
const vec3 CLUB_HALL_MAX = vec3(22.0, 203.0, 16.0);
const vec3 CLUB_BALL = vec3(0.5, 200.5, 0.5);         // 미러볼 중심
const vec3 CLUB_LASER = vec3(0.5, 196.0, -12.5);      // 레이저 발사점 (DJ 부스)
const float CLUB_SPOT_Y = 201.6;                      // 무빙 라이트 높이

bool club_active(ivec3 camBlock) {
    return camBlock.y >= 188 && camBlock.y <= 230 && abs(camBlock.x) <= 48 && abs(camBlock.z) <= 42;
}

vec3 club_color(int i) {
    i = i - (i / 5) * 5;
    if (i == 0) return vec3(1.00, 0.10, 0.70);   // 마젠타
    if (i == 1) return vec3(0.10, 0.80, 1.00);   // 시안
    if (i == 2) return vec3(0.55, 0.20, 1.00);   // 보라
    if (i == 3) return vec3(1.00, 0.45, 0.10);   // 주황
    return vec3(0.20, 1.00, 0.40);               // 초록
}

float club_hash(vec2 p) {
    return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
}

float club_beat(float s) {
    return s * CLUB_BPM / 60.0;
}

vec3 club_spot_pos(int i) {
    return vec3(-14.5 + 6.0 * float(i), CLUB_SPOT_Y, (i - (i / 2) * 2) == 0 ? -5.5 : 6.5);
}

vec3 club_spot_dir(int i, float s) {
    float fi = float(i);
    float pan = fi * 1.7 + 1.1 * sin(CLUB_TAU * 48.0 / 1200.0 * s + fi * 1.3);
    float tilt = 0.55 + 0.35 * sin(CLUB_TAU * 70.0 / 1200.0 * s + fi * 2.1);
    return vec3(sin(tilt) * cos(pan), -cos(tilt), sin(tilt) * sin(pan));
}

int club_spot_color(int i, float s) {
    return i + int(floor(club_beat(s) / 8.0));
}

bool club_lasers_on(float s) {
    return int(floor(club_beat(s) / 16.0)) % 2 == 1;
}

// 레이저 판의 법선: 거의 수평인 판이 위아래로 기울며 좌우로 돈다
vec3 club_laser_normal(int j, float s) {
    float fj = float(j);
    float tilt = -0.18 + 0.16 * sin(CLUB_TAU * 90.0 / 1200.0 * s + fj * 2.0) + 0.12 * (fj - 1.0);
    float yaw = 0.45 * sin(CLUB_TAU * 40.0 / 1200.0 * s + fj * 1.7);
    // 앞(+z)으로 뻗는 판: 기본 법선 (0,1,0) 을 x축으로 tilt, y축으로 yaw 회전
    vec3 n = vec3(0.0, cos(tilt), -sin(tilt));
    return vec3(n.x * cos(yaw) + n.z * sin(yaw), n.y, -n.x * sin(yaw) + n.z * cos(yaw));
}

// lit: 바닐라 조명까지 적용된 색, albedo: 텍스처 × 블록 색(AO), p: 월드 좌표, s: 초
vec3 club_light(vec3 lit, vec3 albedo, vec3 p, float s) {
    if (any(lessThan(p, CLUB_MIN)) || any(greaterThan(p, CLUB_MAX))) {
        return lit;
    }
    float beat = club_beat(s);
    float kick = exp(-fract(beat) * 5.0);
    vec3 outc = lit * 0.42;          // 클럽은 어둡게
    vec3 add = vec3(0.0);            // 표면을 비추는 빛 (텍스처 색에 곱함)
    bool hall = all(greaterThanEqual(p, CLUB_HALL_MIN)) && all(lessThanEqual(p, CLUB_HALL_MAX));
    if (!hall) {
        // 홀 밖 방/복도: 보랏빛 네온이 은은하게 숨 쉼
        add += vec3(0.45, 0.12, 0.75) * (0.10 + 0.05 * kick);
        return outc + albedo * add;
    }

    // 무빙 라이트
    for (int i = 0; i < 6; i++) {
        vec3 to = p - club_spot_pos(i);
        float d = length(to);
        float c = dot(to / max(d, 0.001), club_spot_dir(i, s));
        float cone = smoothstep(0.975, 0.992, c);
        add += club_color(club_spot_color(i, s)) * cone * (2.4 / (1.0 + d * d / 160.0));
    }

    // 미러볼 빛 점
    vec3 v = p - CLUB_BALL;
    float vl = length(v);
    if (vl > 1.0) {
        v /= vl;
        float az = atan(v.z, v.x) + CLUB_TAU * 30.0 / 1200.0 * s;
        float el = asin(clamp(v.y, -1.0, 1.0));
        vec2 g = vec2(az / CLUB_TAU * 72.0, el / 3.14159265 * 36.0);
        vec2 cell = floor(g);
        float tw = club_hash(cell);
        float dotv = smoothstep(0.24, 0.10, length(fract(g) - 0.5)) * step(0.35, tw);
        add += vec3(0.85, 0.9, 1.0) * dotv * (0.55 + 0.45 * tw);
    }

    // 홀 전체 색 펄스 (4마디마다 색 변경)
    add += club_color(int(floor(beat / 16.0))) * 0.12 * (0.5 + kick);

    // 스트로브: 32박자 중 마지막 두 박에 한 번씩 (초당 약 2회, 약하게)
    float bar = mod(beat, 32.0);
    if (bar >= 30.0) {
        add += vec3(exp(-fract(beat) * 14.0) * 0.55);
    }

    outc += albedo * add;

    // LED 댄스 플로어 (바닥 블록 윗면, 2x2 타일)
    if (abs(p.y - (CLUB_Y0 + 1.0)) < 0.02 && p.x >= -16.0 && p.x <= 17.0 && p.z >= -10.0 && p.z <= 11.0) {
        vec2 tile = floor(p.xz / 2.0);
        float h = club_hash(tile + floor(beat / 2.0) * 0.25);
        float on = step(0.3, h);
        vec3 tc = club_color(int(floor(h * 5.0)) + int(floor(beat / 4.0)));
        vec2 f = abs(fract(p.xz / 2.0) - 0.5);
        float edge = smoothstep(0.5, 0.44, max(f.x, f.y));   // 타일 사이 어두운 줄눈
        outc = outc * 0.35 + tc * on * edge * (0.35 + 0.75 * kick);
    }

    // 레이저 선 (발사점 앞쪽 표면에만)
    if (club_lasers_on(s) && p.z > CLUB_LASER.z + 0.5) {
        for (int j = 0; j < 3; j++) {
            float dd = abs(dot(p - CLUB_LASER, club_laser_normal(j, s)));
            float line = smoothstep(0.07, 0.0, dd);
            vec3 lc = (j == 1) ? vec3(1.0, 0.15, 0.2) : vec3(0.25, 1.0, 0.3);
            outc += lc * line * 1.2;
        }
    }
    return outc;
}

#endif
