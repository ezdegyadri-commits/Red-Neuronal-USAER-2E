package mx.usaer02e.portal;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.pm.ResolveInfo;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.view.Gravity;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import java.util.List;

/** Browser-owned portal: no WebView, JS bridge, tokens or copied school data. */
public final class LauncherActivity extends Activity {
    private static final Uri PORTAL = Uri.parse("https://red-neuronal-usaer-2e.streamlit.app/");
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        showWelcome();
        // Restoring the launcher must not open a second portal session.
        if (state == null) openPortal();
    }

    private void showWelcome() {
        LinearLayout page = new LinearLayout(this);
        page.setOrientation(LinearLayout.VERTICAL);
        page.setGravity(Gravity.CENTER);
        int pad = (int)(24 * getResources().getDisplayMetrics().density);
        page.setPadding(pad, pad, pad, pad);
        page.setBackgroundColor(Color.rgb(243, 248, 249));
        TextView title = new TextView(this);
        title.setText("USAER 02E"); title.setTextSize(30); title.setGravity(Gravity.CENTER);
        TextView detail = new TextView(this);
        detail.setText("Tu plataforma, con los mismos permisos y funciones.\nNecesitas conexión a internet.");
        detail.setTextSize(17); detail.setGravity(Gravity.CENTER); detail.setPadding(0,pad,0,pad);
        Button open = new Button(this);
        open.setText("Abrir plataforma"); open.setTextSize(18); open.setMinHeight(pad*3);
        open.setOnClickListener(new android.view.View.OnClickListener() {
            @Override public void onClick(android.view.View v) { openPortal(); }
        });
        page.addView(title); page.addView(detail); page.addView(open);
        setContentView(page);
    }

    private void openPortal() {
        Intent view = new Intent(Intent.ACTION_VIEW, PORTAL);
        view.addCategory(Intent.CATEGORY_BROWSABLE);
        String browser = customTabsBrowser(view);
        if (browser != null) {
            // Official Custom Tabs protocol, with no privileged session binder.
            Bundle extras = new Bundle();
            extras.putBinder("android.support.customtabs.extra.SESSION", null);
            view.putExtras(extras);
            view.putExtra("android.support.customtabs.extra.TOOLBAR_COLOR", Color.rgb(8,126,139));
            view.putExtra("android.support.customtabs.extra.TITLE_VISIBILITY", 1);
            view.setPackage(browser);
        }
        try { startActivity(view); finish(); }
        catch (ActivityNotFoundException ex) {
            // A browser may have been removed between resolving and starting.
            try {
                startActivity(new Intent(Intent.ACTION_VIEW, PORTAL).addCategory(Intent.CATEGORY_BROWSABLE));
                finish();
            } catch (ActivityNotFoundException unavailable) {
                new android.app.AlertDialog.Builder(this).setTitle("Necesitas un navegador")
                    .setMessage("Instala o habilita Chrome u otro navegador para abrir la plataforma.")
                    .setPositiveButton("Entendido", new android.content.DialogInterface.OnClickListener() {
                        @Override public void onClick(android.content.DialogInterface d, int w) { d.dismiss(); }
                    }).show();
            }
        }
    }

    private String customTabsBrowser(Intent view) {
        PackageManager pm = getPackageManager();
        List<ResolveInfo> browsers = pm.queryIntentActivities(view, 0);
        ResolveInfo preferred = pm.resolveActivity(view, 0);
        if (preferred != null && supportsTabs(pm, preferred.activityInfo.packageName))
            return preferred.activityInfo.packageName;
        for (ResolveInfo item : browsers)
            if (supportsTabs(pm, item.activityInfo.packageName)) return item.activityInfo.packageName;
        return null;
    }

    private boolean supportsTabs(PackageManager pm, String pkg) {
        Intent service = new Intent("android.support.customtabs.action.CustomTabsService").setPackage(pkg);
        return pm.resolveService(service, 0) != null;
    }
}
