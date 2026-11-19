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
import android.os.Build;
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

import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.Inet4Address;
import java.net.InetAddress;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * NEXUS sur le téléphone : la page du NEXUS du PC, en plein écran, sans navigateur.
 *
 * - Au premier lancement, un écran d'appairage demande : le nom du téléphone, l'adresse du PC (affichée dans
 *   📱 Téléphone, sur le PC) et le code à 6 chiffres affiché sous le QR code. L'appli s'appaire elle-même
 *   (POST /api/pair/claim) et garde le cookie d'appairage ; le QR code n'est pas nécessaire.
 * - Appairage révoqué sur le PC : le PC renvoie vers /pair, l'appli rouvre son écran d'appairage.
 * - Seules les adresses du réseau local sont acceptées : NEXUS n'est jamais ouvert sur Internet.
 * - PC éteint ou autre Wi-Fi : écran « NEXUS injoignable » avec Réessayer / Changer d'adresse.
 * - Les liens vers d'autres sites (GitHub…) s'ouvrent dans le navigateur du téléphone.
 */
public class MainActivity extends Activity {

    private static final String PREFS = "nexus";
    private static final String CLE_ADRESSE = "adresse";
    private static final String CLE_NOM = "nom";
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
            montrerAppairage(null, null, null);
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
                Uri u = Uri.parse(url);
                if (memeNexus(u) && "/pair".equals(u.getPath())) {
                    // le PC ne reconnaît pas (ou plus) ce téléphone : écran d'appairage de l'appli
                    v.stopLoading();
                    v.post(() -> montrerAppairage(null, adresse,
                            "Ce téléphone n'est pas (ou plus) appairé : entre un nouveau code."));
                }
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
        box.addView(boutonDiscret("Changer d'adresse", v -> montrerAppairage(null, adresse, null)));
        ecranErreur = box;
        racine.addView(box, plein());
    }

    private void cacherErreur() {
        if (ecranErreur != null) {
            racine.removeView(ecranErreur);
            ecranErreur = null;
        }
    }

    // ------------------------------------------------------------------ appairage

    /** Écran d'appairage : nom du téléphone, adresse du PC, code affiché sous le QR code. */
    private void montrerAppairage(String nom, String adr, String erreur) {
        racine.removeAllViews();
        if (web != null) {
            web.destroy();
            web = null;
        }
        ecranErreur = null;
        LinearLayout box = colonne();
        box.addView(titre("NEXUS"));
        box.addView(texte("Appairer ce téléphone avec le NEXUS du PC."));

        box.addView(etiquette("1. Nom du téléphone"));
        EditText champNom = champ(nom != null ? nom : prefs().getString(CLE_NOM, Build.MODEL),
                "ex. Téléphone de Léa", InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_CAP_SENTENCES);
        box.addView(champNom, largeur());

        box.addView(etiquette("2. Adresse du PC"));
        EditText champAdr = champ(adr != null ? adr : prefs().getString(CLE_ADRESSE, ADRESSE_DEFAUT), EXEMPLE,
                InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        box.addView(champAdr, largeur());
        box.addView(petit("Sur le PC : 📱 Téléphone → « Actif sur le Wi-Fi : http://… »."));

        box.addView(etiquette("3. Code d'appairage"));
        EditText champCode = champ("", "000000", InputType.TYPE_CLASS_NUMBER);
        champCode.setTextSize(TypedValue.COMPLEX_UNIT_SP, 28);
        champCode.setLetterSpacing(.4f);
        champCode.setGravity(Gravity.CENTER);
        champCode.setImeOptions(EditorInfo.IME_ACTION_GO);
        champCode.setFilters(new android.text.InputFilter[]{new android.text.InputFilter.LengthFilter(7)});
        box.addView(champCode, largeur());
        box.addView(petit("Sur le PC : 📱 Téléphone → « Afficher le QR code » : le code à 6 chiffres est à côté "
                + "du QR code. Valable 2 minutes, une seule fois. Pas besoin de scanner le QR code."));

        TextView msg = petit(erreur == null ? "" : erreur);
        msg.setTextColor(ROUGE);
        box.addView(msg);

        Button go = bouton("Appairer", null);
        View.OnClickListener valider = v -> appairer(champNom.getText().toString(), champAdr.getText().toString(),
                champCode.getText().toString(), go, msg);
        go.setOnClickListener(valider);
        champCode.setOnEditorActionListener((v, action, ev) -> {
            if (action == EditorInfo.IME_ACTION_GO || (ev != null && ev.getKeyCode() == KeyEvent.KEYCODE_ENTER)) {
                valider.onClick(v);
                return true;
            }
            return false;
        });
        box.addView(go);
        if (prefs().getString(CLE_ADRESSE, null) != null) {
            box.addView(boutonDiscret("Déjà appairé : ouvrir NEXUS", v -> {
                adresse = prefs().getString(CLE_ADRESSE, adresse);
                ouvrirNexus(null);
            }));
        }
        android.widget.ScrollView defile = new android.widget.ScrollView(this);
        defile.setFillViewport(true);
        defile.setBackgroundColor(NOIR);
        defile.addView(box);
        racine.addView(defile, plein());
        if (champAdr.getText().length() <= ADRESSE_DEFAUT.length()) champAdr.requestFocus();
        else champCode.requestFocus();
    }

    private void appairer(String nomSaisi, String adrSaisie, String codeSaisi, Button go, TextView msg) {
        String nom = nomSaisi.trim();
        String a = normaliser(adrSaisie);
        String code = codeSaisi.replaceAll("[^0-9]", "");
        msg.setTextColor(ROUGE);
        if (nom.isEmpty()) { msg.setText("Donne un nom à ce téléphone (il s'affichera sur le PC)."); return; }
        if (a == null) { msg.setText("Adresse non valable. Exemple : " + EXEMPLE); return; }
        if (code.length() != 6) { msg.setText("Le code fait 6 chiffres."); return; }
        go.setEnabled(false);
        msg.setTextColor(GRIS);
        msg.setText("Appairage…");
        new Thread(() -> {
            String erreur;
            if (!estLocale(Uri.parse(a).getHost())) {
                erreur = "Seules les adresses du réseau de la maison sont acceptées (192.168.x.x, 10.x.x.x, 172.16 à 31.x.x).";
            } else {
                erreur = reclamer(a, code, nom);
            }
            final String e = erreur;
            runOnUiThread(() -> {
                if (e == null) {
                    adresse = a;
                    prefs().edit().putString(CLE_ADRESSE, a).putString(CLE_NOM, nom).apply();
                    ouvrirNexus(null);
                } else {
                    go.setEnabled(true);
                    msg.setTextColor(ROUGE);
                    msg.setText(e);
                }
            });
        }).start();
    }

    /** POST /api/pair/claim ; le cookie d'appairage reçu est donné à la page. Renvoie null si c'est bon. */
    private String reclamer(String base, String code, String nom) {
        HttpURLConnection c = null;
        try {
            c = (HttpURLConnection) new URL(base + "/api/pair/claim").openConnection();
            c.setConnectTimeout(6000);
            c.setReadTimeout(8000);
            c.setRequestMethod("POST");
            c.setDoOutput(true);
            c.setRequestProperty("Content-Type", "application/json");
            c.setRequestProperty("User-Agent", "Mozilla/5.0 (Linux; Android " + Build.VERSION.RELEASE + "; "
                    + Build.MODEL + ") NEXUSApp/" + versionAppli());
            byte[] corps = new JSONObject().put("code", code).put("name", nom).toString()
                    .getBytes(StandardCharsets.UTF_8);
            try (OutputStream o = c.getOutputStream()) {
                o.write(corps);
            }
            int statut = c.getResponseCode();
            if (statut == 200) {
                CookieManager cm = CookieManager.getInstance();
                cm.setAcceptCookie(true);
                for (Map.Entry<String, List<String>> h : c.getHeaderFields().entrySet()) {
                    if (h.getKey() != null && h.getKey().equalsIgnoreCase("Set-Cookie")) {
                        for (String v : h.getValue()) cm.setCookie(base, v);
                    }
                }
                cm.flush();
                return null;
            }
            String err = "";
            try (InputStream in = c.getErrorStream()) {
                if (in != null) err = new JSONObject(lire(in)).optString("error", "");
            } catch (Exception ignore) {
                // réponse sans JSON : message générique
            }
            if (statut == 403 && err.contains("invalide")) {
                return "Code refusé : il a expiré ou a déjà servi (un scan du QR code l'utilise). "
                        + "Sur le PC, « Afficher le QR code » pour un nouveau code.";
            }
            if (statut == 403) {
                return "Le PC refuse ce téléphone : l'accès téléphone est-il activé sur le PC ? " + err;
            }
            return "Réponse inattendue du PC (" + statut + ") " + err;
        } catch (java.net.SocketTimeoutException | java.net.ConnectException | java.net.NoRouteToHostException e) {
            return "PC injoignable à " + base + " : PC allumé, NEXUS ouvert, même Wi-Fi, pare-feu autorisé ?";
        } catch (Exception e) {
            return "Appairage impossible : " + e.getMessage();
        } finally {
            if (c != null) c.disconnect();
        }
    }

    private static String lire(InputStream in) throws java.io.IOException {
        ByteArrayOutputStream b = new ByteArrayOutputStream();
        byte[] buf = new byte[4096];
        int n;
        while ((n = in.read(buf)) > 0 && b.size() < 65536) b.write(buf, 0, n);
        return b.toString("UTF-8");
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

    private TextView etiquette(String t) {
        TextView v = texte(t);
        v.setTextColor(ROUGE);
        v.setTypeface(Typeface.MONOSPACE, Typeface.BOLD);
        v.setPadding(0, dp(22), 0, 0);
        return v;
    }

    private EditText champ(String valeur, String exemple, int type) {
        EditText e = new EditText(this);
        e.setText(valeur);
        e.setTextColor(TEXTE);
        e.setHintTextColor(GRIS);
        e.setHint(exemple);
        e.setSingleLine(true);
        e.setInputType(type);
        e.setSelection(e.getText().length());
        return e;
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
