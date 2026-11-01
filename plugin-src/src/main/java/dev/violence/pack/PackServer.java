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
            http.setExecutor(Executors.newFixedThreadPool(2));
            http.start();
            plugin.getLogger().info("리소스팩 HTTP 서버 시작: 포트 " + port);
        } catch (IOException e) {
            plugin.getLogger().warning("리소스팩 HTTP 서버 시작 실패 (포트 " + port + "): " + e.getMessage());
        }
    }

    public void reload() {
        File f = packFile();
        if (!f.isFile()) {
            plugin.getLogger().warning("리소스팩 파일이 없습니다: " + f + "  (resourcepack 폴더를 tools/build_pack.py 로 압축해 넣으세요)");
            zip = null;
            return;
        }
        try {
            zip = Files.readAllBytes(f.toPath());
            sha1 = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-1").digest(zip));
            plugin.getLogger().info("리소스팩 로드: " + f.getName() + " (" + zip.length / 1024 + "KB, sha1 " + sha1 + ")");
        } catch (Exception e) {
            plugin.getLogger().warning("리소스팩 읽기 실패: " + e);
            zip = null;
        }
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

    public void send(Player p) {
        if (!plugin.getConfig().getBoolean("resource-pack.enabled", true) || sha1 == null) return;
        try {
            ResourcePackInfo info = ResourcePackInfo.resourcePackInfo(packId, URI.create(url()), sha1);
            p.sendResourcePacks(ResourcePackRequest.resourcePackRequest()
                    .packs(info)
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
    }
}
