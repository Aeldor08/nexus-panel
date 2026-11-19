// Appli Android NEXUS : télécommande du NEXUS du PC sur le Wi-Fi de la maison (voir android/LISEZMOI.md)
pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}
rootProject.name = "NEXUS"
include(":app")
