plugins {
    id("com.android.application")
}

// Version de l'appli = VERSION de NEXUS (fichier à la racine du dépôt)
val nexusVersion = rootProject.file("../VERSION").takeIf { it.isFile }?.readText()?.trim() ?: "1.0.0"
val parts = nexusVersion.split(".").mapNotNull { it.toIntOrNull() } + listOf(0, 0, 0)
// Révision de l'appli pour une même version de NEXUS (à augmenter à chaque nouvel APK de la même version)
val revisionAppli = 2

android {
    namespace = "io.github.aeldor08.nexus"
    compileSdk = 35

    defaultConfig {
        applicationId = "io.github.aeldor08.nexus"
        minSdk = 24
        targetSdk = 35
        versionCode = (parts[0] * 10000 + parts[1] * 100 + parts[2]) * 100 + revisionAppli
        versionName = "$nexusVersion-$revisionAppli"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            // Clé de signature de débogage d'Android Studio / du SDK (~/.android/debug.keystore, créée
            // automatiquement) : suffisant pour installer l'APK à la main. Une mise à jour de l'appli doit être
            // signée par la même clé, donc construite sur le même PC.
            signingConfig = signingConfigs.getByName("debug")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}
