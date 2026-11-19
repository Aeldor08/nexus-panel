package io.github.aeldor08.nexus;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Bitmap;
import android.graphics.Color;
import android.graphics.Typeface;
import android.net.Uri;
import android.os.Bundle;
import android.text.InputType;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.KeyEvent;
import android.view.View;
import android.view.ViewGroup;
import android.view.inputmethod.EditorInfo;
import android.webkit.CookieManager;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.net.Inet4Address;
import java.net.InetAddress;
import java.util.Locale;

/**
 * NEXUS sur le téléphone : la page du NEXUS du PC, en plein écran, sans navigateur.
 *
 * - Au premier lancement : on demande l'adresse du PC (celle affichée dans 📱 Téléphone, sur le PC).
 * - Le téléphone s'appaire ensuite comme avant (page /pair, code à 6 chiffres) ; le cookie d'appairage est
 *   gardé par l'appli.
 * - Seules les adresses du réseau local sont acceptées : NEXUS n'est jamais ouvert sur Internet.
 * - PC éteint ou autre Wi-Fi : écran « NEXUS injoignable » avec Réessayer / Changer d'adresse.
 * - Les liens vers d'autres sites (GitHub…) s'ouvrent dans le navigateur du téléphone.
 */
public class MainActivity extends Activity {

    private static final String PREFS = "nexus";
    private static final String CLE_ADRESSE = "adresse";
    // Pré-rempli au premier lancement ; l'exemple montré dans le champ vide et les messages
    private static final String ADRESSE_DEFAUT = "http://";
    private static final String EXEMPLE = "http://192.168.x.x:8765";
    private static final int CHOIX_FICHIER = 41;

    private static final int NOIR = Color.rgb(5, 2, 11);
    private static final int TEXTE = Color.rgb(230, 225, 240);
    private static final int GRIS = Color.rgb(150, 140, 170);
    private static final int ROUGE = Color.rgb(255, 36, 58);

    private FrameLayout racine;
    private WebView web;
    private View ecranErreur;
    private String adresse;
    private ValueCallback<Uri[]> fichiersEnAttente;

    @Override
    protected void onCreate(Bundle etat) {
        super.onCreate(etat);
        racine = new FrameLayout(this);
        racine.setBackgroundColor(NOIR);
        setContentView(racine);

        adresse = prefs().getString(CLE_ADRESSE, null);
        if (adresse == null) {
            montrerReglage(ADRESSE_DEFAUT, null);
        } else {
            ouvrirNexus(etat);
        }
    }

    private SharedPreferences prefs() {
        return getSharedPreferences(PREFS, MODE_PRIVATE);
    }

    // ------------------------------------------------------------------ page NEXUS

    @SuppressLint("SetJavaScriptEnabled")
    private void ouvrirNexus(Bundle etat) {
        racine.removeAllViews();
        ecranErreur = null;
        web = new WebView(this);
        web.setBackgroundColor(NOIR);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);                 // disposition des blocs, thème, réglages (localStorage)
        s.setMediaPlaybackRequiresUserGesture(true);
        s.setAllowFileAccess(false);
        s.setAllowContentAccess(false);
        s.setUserAgentString(s.getUserAgentString() + " NEXUSApp/" + versionAppli());
        CookieManager.getInstance().setAcceptCookie(true);   // cookie d'appairage du téléphone

        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest req) {
                Uri u = req.getUrl();
                if (memeNexus(u)) return false;            // reste dans l'appli
                ouvrirAilleurs(u);                         // GitHub, Discord… : navigateur du téléphone
                return true;
            }

            @Override
            public void onPageStarted(WebView v, String url, Bitmap favicon) {
                cacherErreur();
            }

            @Override
            public void onReceivedError(WebView v, WebResourceRequest req, WebResourceError err) {
                if (req.isForMainFrame()) montrerErreur(String.valueOf(err.getDescription()));
            }
        });
        web.setWebChromeClient(new WebChromeClient() {
            // Souvenirs : choisir une photo dans la galerie du téléphone
            @Override
            public boolean onShowFileChooser(WebView v, ValueCallback<Uri[]> rappel, FileChooserParams params) {
                if (fichiersEnAttente != null) fichiersEnAttente.onReceiveValue(null);
                fichiersEnAttente = rappel;
                try {
                    startActivityForResult(params.createIntent(), CHOIX_FICHIER);
                } catch (ActivityNotFoundException e) {
                    fichiersEnAttente = null;
                    return false;
                }
                return true;
            }
        });

        racine.addView(web, new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT));
        if (etat != null && web.restoreState(etat) != null) return;
        web.loadUrl(adresse + "/#accueil");
    }

    private boolean memeNexus(Uri u) {
        Uri base = Uri.parse(adresse);
        return u != null && base.getHost() != null
                && base.getHost().equalsIgnoreCase(u.getHost())
                && port(base) == port(u)
                && ("http".equals(u.getScheme()) || "https".equals(u.getScheme()));
    }

    private static int port(Uri u) {
        if (u.getPort() != -1) return u.getPort();
        return "https".equals(u.getScheme()) ? 443 : 80;
    }

    private void ouvrirAilleurs(Uri u) {
        try {
            startActivity(new Intent(Intent.ACTION_VIEW, u));
        } catch (ActivityNotFoundException ignore) {
            // aucune appli pour ce lien : on ne fait rien
        }
    }

    @Override
    protected void onActivityResult(int code, int resultat, Intent donnees) {
        if (code == CHOIX_FICHIER && fichiersEnAttente != null) {
            fichiersEnAttente.onReceiveValue(WebChromeClient.FileChooserParams.parseResult(resultat, donnees));
            fichiersEnAttente = null;
            return;
        }
        super.onActivityResult(code, resultat, donnees);
    }

    // ------------------------------------------------------------------ NEXUS injoignable

    private void montrerErreur(String detail) {
        if (ecranErreur != null) return;
        LinearLayout box = colonne();
        box.addView(titre("NEXUS injoignable"));
        box.addView(texte("Le PC est-il allumé, NEXUS ouvert, et le téléphone sur le même Wi-Fi ?\n\n"
                + "Sur le PC : 📱 Téléphone → l'accès doit être actif (et le pare-feu autorisé)."));
        box.addView(petit(adresse + (detail.isEmpty() ? "" : "\n" + detail)));
        box.addView(bouton("Réessayer", v -> { cacherErreur(); web.reload(); }));
        box.addView(boutonDiscret("Changer d'adresse", v -> montrerReglage(adresse, null)));
        ecranErreur = box;
        racine.addView(box, plein());
    }

    private void cacherErreur() {
        if (ecranErreur != null) {
            racine.removeView(ecranErreur);
            ecranErreur = null;
        }
    }

    // ------------------------------------------------------------------ réglage de l'adresse

    private void montrerReglage(String valeur, String erreur) {
        racine.removeAllViews();
        if (web != null) {
            web.destroy();
            web = null;
        }
        ecranErreur = null;
        LinearLayout box = colonne();
        box.addView(titre("NEXUS"));
        box.addView(texte("Adresse du PC, affichée sur le PC dans 📱 Téléphone (« Actif sur le Wi-Fi »)."));
        EditText champ = new EditText(this);
        champ.setText(valeur);
        champ.setTextColor(TEXTE);
        champ.setHintTextColor(GRIS);
        champ.setHint(EXEMPLE);
        champ.setSingleLine(true);
        champ.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        champ.setImeOptions(EditorInfo.IME_ACTION_GO);
        champ.setSelection(champ.getText().length());
        box.addView(champ, largeur());
        if (erreur != null) {
            TextView e = petit(erreur);
            e.setTextColor(ROUGE);
            box.addView(e);
        }
        View.OnClickListener valider = v -> enregistrer(champ.getText().toString());
        champ.setOnEditorActionListener((v, action, ev) -> {
            if (action == EditorInfo.IME_ACTION_GO
                    || (ev != null && ev.getKeyCode() == KeyEvent.KEYCODE_ENTER)) {
                valider.onClick(v);
                return true;
            }
            return false;
        });
        box.addView(bouton("Se connecter", valider));
        box.addView(petit("Ensuite, si NEXUS le demande, tape le code d'appairage affiché sur le PC "
                + "(📱 Téléphone → Afficher le QR code). Seul le réseau de la maison est accepté."));
        racine.addView(box, plein());
    }

    private void enregistrer(String saisie) {
        String a = normaliser(saisie);
        if (a == null) {
            montrerReglage(saisie, "Adresse non valable. Exemple : " + EXEMPLE);
            return;
        }
        new Thread(() -> {
            boolean locale = estLocale(Uri.parse(a).getHost());
            runOnUiThread(() -> {
                if (!locale) {
                    montrerReglage(saisie, "Seules les adresses du réseau de la maison sont acceptées "
                            + "(192.168.x.x, 10.x.x.x, 172.16 à 31.x.x).");
                    return;
                }
                adresse = a;
                prefs().edit().putString(CLE_ADRESSE, a).apply();
                ouvrirNexus(null);
            });
        }).start();
    }

    /** « pc.lan:8765 » → « http://pc.lan:8765 » ; null si ce n'est pas une adresse. */
    static String normaliser(String saisie) {
        String s = saisie == null ? "" : saisie.trim();
        if (s.isEmpty()) return null;
        if (!s.contains("://")) s = "http://" + s;
        Uri u = Uri.parse(s);
        String sch = u.getScheme() == null ? "" : u.getScheme().toLowerCase(Locale.ROOT);
        if (!sch.equals("http") && !sch.equals("https")) return null;
        String h = u.getHost();
        if (h == null || h.isEmpty()) return null;
        return sch + "://" + h + (u.getPort() != -1 ? ":" + u.getPort() : "");
    }

    /** Adresse du réseau local seulement (jamais une adresse Internet). Résolution DNS : hors du fil principal. */
    static boolean estLocale(String hote) {
        if (hote == null) return false;
        String h = hote.toLowerCase(Locale.ROOT);
        try {
            for (InetAddress a : InetAddress.getAllByName(h)) {
                if (!(a instanceof Inet4Address)) continue;
                byte[] b = a.getAddress();
                int b0 = b[0] & 0xff, b1 = b[1] & 0xff;
                if (b0 == 10 || (b0 == 192 && b1 == 168) || (b0 == 172 && b1 >= 16 && b1 <= 31)
                        || (b0 == 169 && b1 == 254)) return true;
            }
        } catch (Exception ignore) {
            // nom inconnu : seulement les noms locaux habituels (le PC peut être éteint pendant le réglage)
        }
        return h.endsWith(".local") || h.endsWith(".lan") || h.endsWith(".home");
    }

    // ------------------------------------------------------------------ cycle de vie

    @Override
    public void onBackPressed() {
        if (web != null && ecranErreur == null && web.canGoBack()) {
            web.goBack();
            return;
        }
        super.onBackPressed();
    }

    @Override
    protected void onSaveInstanceState(Bundle etat) {
        super.onSaveInstanceState(etat);
        if (web != null) web.saveState(etat);
    }

    @Override
    protected void onPause() {
        super.onPause();
        CookieManager.getInstance().flush();          // l'appairage survit à la fermeture de l'appli
        if (web != null) web.onPause();
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (web != null) web.onResume();
    }

    @Override
    protected void onDestroy() {
        if (web != null) web.destroy();
        super.onDestroy();
    }

    // ------------------------------------------------------------------ petits éléments d'interface

    private String versionAppli() {
        try {
            return getPackageManager().getPackageInfo(getPackageName(), 0).versionName;
        } catch (Exception e) {
            return "?";
        }
    }

    private int dp(int v) {
        return (int) TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP, v, getResources().getDisplayMetrics());
    }

    private LinearLayout colonne() {
        LinearLayout l = new LinearLayout(this);
        l.setOrientation(LinearLayout.VERTICAL);
        l.setGravity(Gravity.CENTER_VERTICAL);
        l.setBackgroundColor(NOIR);
        l.setPadding(dp(28), dp(28), dp(28), dp(28));
        return l;
    }

    private FrameLayout.LayoutParams plein() {
        return new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT);
    }

    private LinearLayout.LayoutParams largeur() {
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT);
        p.topMargin = dp(12);
        return p;
    }

    private TextView titre(String t) {
        TextView v = new TextView(this);
        v.setText(t);
        v.setTextColor(ROUGE);
        v.setTextSize(TypedValue.COMPLEX_UNIT_SP, 28);
        v.setTypeface(Typeface.MONOSPACE, Typeface.BOLD);
        v.setLetterSpacing(.15f);
        return v;
    }

    private TextView texte(String t) {
        TextView v = new TextView(this);
        v.setText(t);
        v.setTextColor(TEXTE);
        v.setTextSize(TypedValue.COMPLEX_UNIT_SP, 16);
        v.setPadding(0, dp(14), 0, 0);
        return v;
    }

    private TextView petit(String t) {
        TextView v = texte(t);
        v.setTextColor(GRIS);
        v.setTextSize(TypedValue.COMPLEX_UNIT_SP, 13);
        return v;
    }

    private Button bouton(String t, View.OnClickListener action) {
        Button b = new Button(this);
        b.setText(t);
        b.setTextColor(Color.WHITE);
        b.setBackgroundColor(ROUGE);
        b.setAllCaps(false);
        b.setOnClickListener(action);
        b.setLayoutParams(largeur());
        return b;
    }

    private Button boutonDiscret(String t, View.OnClickListener action) {
        Button b = bouton(t, action);
        b.setBackgroundColor(Color.TRANSPARENT);
        b.setTextColor(GRIS);
        return b;
    }
}
