package dev.violence.pack;

import com.sun.net.httpserver.HttpServer;
import dev.violence.ViolencePlugin;
import java.io.File;
import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.URI;
import java.nio.file.Files;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.UUID;
import java.util.concurrent.Executors;
import net.kyori.adventure.resource.ResourcePackInfo;
import net.kyori.adventure.resource.ResourcePackRequest;
import net.kyori.adventure.text.Component;
import org.bukkit.entity.Player;

/**
 * 리소스팩 자동 배포. 플러그인에 내장된 작은 HTTP 서버가 resourcepack.zip 을 제공하고
 * 접속한 플레이어에게 필수 리소스팩으로 전송한다.
 * config.yml 의 resource-pack.url 을 지정하면 외부 주소를 대신 사용한다.
 */
public final class PackServer {
    private final ViolencePlugin plugin;
    private HttpServer http;
    private byte[] zip;
    private String sha1;
    private final UUID packId = UUID.nameUUIDFromBytes("violence-pack".getBytes());

    public PackServer(ViolencePlugin plugin) {
        this.plugin = plugin;
    }

    public File packFile() {
        return new File(plugin.getDataFolder(), plugin.getConfig().getString("resource-pack.file", "resourcepack.zip"));
    }

    public void start() {
        if (!plugin.getConfig().getBoolean("resource-pack.enabled", true)) return;
        reload();
        String external = plugin.getConfig().getString("resource-pack.url", "");
        if (external != null && !external.isBlank()) return;
        int port = plugin.getConfig().getInt("resource-pack.port", 8163);
        try {
            http = HttpServer.create(new InetSocketAddress(port), 0);
            http.createContext("/skin/", ex -> {
                // /skin/<uuid>-<sha1>.zip : 플레이어마다 1인칭 팔 스킨 팩
                String path = ex.getRequestURI().getPath();
                String key = path.substring(path.lastIndexOf('/') + 1).replace(".zip", "");
                byte[] data = skinPacks.get(key.contains("-") ? key.substring(0, 36) : key);
                if (data == null) {
                    ex.sendResponseHeaders(404, -1);
                    ex.close();
                    return;
                }
                ex.getResponseHeaders().add("Content-Type", "application/zip");
                ex.sendResponseHeaders(200, data.length);
                try (OutputStream os = ex.getResponseBody()) {
                    os.write(data);
                }
            });
            http.createContext("/violence.zip", ex -> {
                byte[] data = zip;
                if (data == null) {
                    ex.sendResponseHeaders(404, -1);
                    ex.close();
                    return;
                }
                ex.getResponseHeaders().add("Content-Type", "application/zip");
                ex.sendResponseHeaders(200, data.length);
                try (OutputStream os = ex.getResponseBody()) {
                    os.write(data);
                }
            });
            pool = Executors.newFixedThreadPool(2, r -> {
                Thread t = new Thread(r, "violence-pack-http");
                t.setDaemon(true);                 // 서버 종료를 막지 않게
                return t;
            });
            http.setExecutor(pool);
            http.start();
            plugin.getLogger().info("리소스팩 HTTP 서버 시작: 포트 " + port);
            String host = plugin.getConfig().getString("resource-pack.public-host", "");
            if ((host == null || host.isBlank()) && (plugin.getServer().getIp() == null || plugin.getServer().getIp().isBlank())) {
                plugin.getLogger().warning("resource-pack.public-host 가 비어 있어 리소스팩 주소가 127.0.0.1 입니다. "
                        + "같은 컴퓨터에서만 받을 수 있으니 config.yml 에 서버의 외부 주소를 적어 주세요.");
            }
        } catch (IOException | RuntimeException e) {
            http = null;
            plugin.getLogger().warning("리소스팩 HTTP 서버 시작 실패 (포트 " + port + "): " + e.getMessage()
                    + " - 리소스팩을 보내지 않습니다. 다른 포트를 쓰거나 resource-pack.url 에 외부 주소를 지정하세요.");
        }
    }

    public void reload() {
        File f = packFile();
        if (!f.isFile()) {
            plugin.getLogger().warning("리소스팩 파일이 없습니다: " + f + "  (resourcepack 폴더를 tools/build_pack.py 로 압축해 넣으세요)");
            zip = null;
            sha1 = null;   // 없는 파일을 가리키는 해시로 리소스팩을 요구하지 않게
            return;
        }
        try {
            zip = Files.readAllBytes(f.toPath());
            sha1 = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-1").digest(zip));
            plugin.getLogger().info("리소스팩 로드: " + f.getName() + " (" + zip.length / 1024 + "KB, sha1 " + sha1 + ")");
        } catch (Exception e) {
            plugin.getLogger().warning("리소스팩 읽기 실패: " + e);
            zip = null;
            sha1 = null;
        }
    }

    private final java.util.Map<String, byte[]> skinPacks = new java.util.concurrent.ConcurrentHashMap<>();
    private final UUID skinPackId = UUID.nameUUIDFromBytes("violence-skin".getBytes());

    /**
     * 1인칭 팔에 자기 스킨: 스킨을 받아 작은 팩을 만들어 본 리소스팩 위에 덮어 보냄 (비동기).
     * file 이 있으면 그 PNG 를, 없으면 플레이어 프로필의 스킨 주소를 쓴다 (오프라인 서버는 스킨이 없어 기본 팔).
     */
    public void sendSkin(Player p, File file) {
        if (!plugin.getConfig().getBoolean("resource-pack.enabled", true) || http == null || zip == null || p == null) return;
        java.net.URL skinUrl = null;
        boolean slim = false;
        if (file == null) {
            var tex = p.getPlayerProfile().getTextures();
            skinUrl = tex.getSkin();
            slim = tex.getSkinModel() == org.bukkit.profile.PlayerTextures.SkinModel.SLIM;
            if (skinUrl == null) return;
        }
        final java.net.URL url0 = skinUrl;
        final boolean slim0 = slim;
        final byte[] main = zip;
        UUID id = p.getUniqueId();
        plugin.getServer().getScheduler().runTaskAsynchronously(plugin, () -> {
            try {
                java.awt.image.BufferedImage img;
                if (file != null) {
                    img = javax.imageio.ImageIO.read(file);
                } else {
                    java.net.HttpURLConnection c = (java.net.HttpURLConnection) url0.openConnection();
                    c.setConnectTimeout(5000);
                    c.setReadTimeout(5000);
                    try (java.io.InputStream in = c.getInputStream()) {
                        img = javax.imageio.ImageIO.read(in);
                    }
                }
                if (img == null) throw new IOException("PNG 가 아님");
                byte[] pack = SkinPack.build(main, SkinPack.normalize(img, slim0));
                String hash = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-1").digest(pack));
                skinPacks.put(id.toString(), pack);
                plugin.getServer().getScheduler().runTask(plugin, () -> {
                    Player q = plugin.getServer().getPlayer(id);
                    if (q == null || !q.isOnline()) return;
                    String u = baseUrl() + "/skin/" + id + "-" + hash.substring(0, 8) + ".zip";
                    sendPacks(q, ResourcePackInfo.resourcePackInfo(skinPackId, URI.create(u), hash));
                });
            } catch (Exception e) {
                plugin.getLogger().warning("스킨 팩 만들기 실패 (" + p.getName() + "): " + e.getMessage());
                plugin.getServer().getScheduler().runTask(plugin, () -> { if (p.isOnline()) sendPacks(p, null); });
            }
        });
    }

    public void forgetSkin(Player p) {
        skinPacks.remove(p.getUniqueId().toString());
    }

    private String baseUrl() {
        String host = plugin.getConfig().getString("resource-pack.public-host", "");
        if (host == null || host.isBlank()) {
            host = plugin.getServer().getIp();
            if (host == null || host.isBlank()) host = "127.0.0.1";
        }
        return "http://" + host + ":" + plugin.getConfig().getInt("resource-pack.port", 8163);
    }

    private String url() {
        String external = plugin.getConfig().getString("resource-pack.url", "");
        if (external != null && !external.isBlank()) return external;
        String host = plugin.getConfig().getString("resource-pack.public-host", "");
        if (host == null || host.isBlank()) {
            host = plugin.getServer().getIp();
            if (host == null || host.isBlank()) host = "127.0.0.1";
        }
        return "http://" + host + ":" + plugin.getConfig().getInt("resource-pack.port", 8163) + "/violence.zip";
    }

    /** 접속: 스킨이 있으면 받아서 [스킨 팩, 본 팩] 을 함께, 없으면 본 팩만 보냄 */
    public void send(Player p) {
        if (p == null) return;
        if (http != null && zip != null && p.getPlayerProfile().getTextures().getSkin() != null) {
            sendSkin(p, null);
        } else {
            sendPacks(p, null);
        }
    }

    /**
     * 본 팩과 스킨 팩을 한 요청으로 [본 팩, 스킨 팩] 순서로 보냄 → 스킨 팩이 위에 놓여 본 팩의 기본 팔 스킨을 덮는다
     * (26.3 클라이언트에서 확인한 순서).
     */
    private void sendPacks(Player p, ResourcePackInfo skin) {
        if (!plugin.getConfig().getBoolean("resource-pack.enabled", true) || sha1 == null) return;
        String external = plugin.getConfig().getString("resource-pack.url", "");
        boolean usingExternal = external != null && !external.isBlank();
        if (!usingExternal && http == null) return;   // 내장 서버가 꺼져 있으면 받을 수 없는 주소를 보내지 않음
        if (p == null || !p.isOnline()) return;
        try {
            ResourcePackInfo info = ResourcePackInfo.resourcePackInfo(packId, URI.create(url()), sha1);
            java.util.List<ResourcePackInfo> packs = skin == null ? java.util.List.of(info) : java.util.List.of(info, skin);
            p.sendResourcePacks(ResourcePackRequest.resourcePackRequest()
                    .packs(packs)
                    .required(plugin.getConfig().getBoolean("resource-pack.required", true))
                    .prompt(Component.text("VIOLENCE 전용 리소스팩이 필요합니다"))
                    .replace(true)
                    .build());
        } catch (RuntimeException e) {
            plugin.getLogger().warning("리소스팩 전송 실패: " + e);
        }
    }

    public void stop() {
        if (http != null) http.stop(0);
        http = null;
        if (pool != null) pool.shutdownNow();
        pool = null;
    }

    private java.util.concurrent.ExecutorService pool;
}
