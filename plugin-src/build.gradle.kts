plugins {
    java
}

group = "dev.violence"
version = "1.0.0"

java {
    toolchain.languageVersion.set(JavaLanguageVersion.of(25))
}

repositories {
    mavenCentral()
    maven("https://repo.papermc.io/repository/maven-public/")
}

val localPaperApi = providers.gradleProperty("localPaperApi").orNull

dependencies {
    if (localPaperApi != null) {
        compileOnly(fileTree(localPaperApi) { include("*.jar") })
        testImplementation(fileTree(localPaperApi) { include("*.jar") })
    } else {
        compileOnly("io.papermc.paper:paper-api:${providers.gradleProperty("paperVersion").get()}")
        testImplementation("io.papermc.paper:paper-api:${providers.gradleProperty("paperVersion").get()}")
    }
    testImplementation(platform("org.junit:junit-bom:5.13.4"))
    testImplementation("org.junit.jupiter:junit-jupiter")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
}

tasks.withType<JavaCompile>().configureEach {
    options.encoding = "UTF-8"
    options.release.set(25)
    options.compilerArgs.addAll(listOf("-Xlint:deprecation", "-Xlint:unchecked"))
}

tasks.test {
    useJUnitPlatform()
    testLogging {
        events("passed", "failed", "skipped")
        exceptionFormat = org.gradle.api.tasks.testing.logging.TestExceptionFormat.FULL
    }
}

tasks.processResources {
    filteringCharset = "UTF-8"
    val props = mapOf("version" to project.version)
    inputs.properties(props)
    filesMatching("paper-plugin.yml") { expand(props) }
    filesMatching("plugin.yml") { expand(props) }
}

// 빌드 결과물을 서버 폴더(bukkit/plugins)로 복사
val deployToServer by tasks.registering(Copy::class) {
    dependsOn(tasks.jar)
    from(tasks.jar.flatMap { it.archiveFile })
    into(layout.projectDirectory.dir("../bukkit/plugins"))
    rename { "ViolenceCore.jar" }
}
tasks.build { finalizedBy(deployToServer) }
