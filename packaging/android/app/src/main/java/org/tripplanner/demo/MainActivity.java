package org.tripplanner.demo;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.os.Message;
import android.view.ViewGroup;
import android.webkit.CookieManager;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.TextView;
import android.widget.FrameLayout;
import android.widget.Toast;
import com.chaquo.python.Python;
import java.io.ByteArrayInputStream;
import java.net.URI;

/** A local app window. Python runs on this device and owns all planning data. */
public final class MainActivity extends Activity {
    private WebView web;
    private String origin;
    private android.window.OnBackInvokedCallback backCallback;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        TextView loading = new TextView(this);
        loading.setText("TripPlanner is opening your local planner…");
        loading.setPadding(28, 70, 28, 28);
        setContentView(loading);
        new Thread(() -> {
            try {
                String url = Python.getInstance().getModule("android_runtime")
                    .callAttr("start", getFilesDir().getAbsolutePath()+"/tripplanner").toString();
                URI parsed = URI.create(url);
                origin = parsed.getScheme()+"://"+parsed.getAuthority();
                runOnUiThread(() -> showPlanner(url));
            } catch (Exception error) {
                android.util.Log.e("TripPlanner", "Local startup failed", error);
                runOnUiThread(() -> loading.setText("TripPlanner could not start. Close and reopen the app. Your saved trips have not been reset."));
            }
        }, "TripPlanner-start").start();
    }

    private boolean internal(String url) {
        try {
            URI u = new URI(url);
            return u.getRawUserInfo() == null && origin.equals(u.getScheme()+"://"+u.getRawAuthority());
        } catch (Exception error) { return false; }
    }

    private boolean safeExternal(String url) {
        try {
            URI u = new URI(url);
            String host = u.getHost();
            return "https".equals(u.getScheme()) && u.getRawUserInfo() == null
                && host != null && host.matches("(?i)[a-z][a-z0-9.-]*\\.[a-z]{2,}")
                && !host.equalsIgnoreCase("localhost") && !host.toLowerCase(java.util.Locale.ROOT).endsWith(".localhost")
                && !url.contains("\\") && !url.matches("(?s).*\\s.*");
        } catch (Exception error) { return false; }
    }

    private void external(String url) {
        if (!safeExternal(url)) return;
        try { startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url))); }
        catch (ActivityNotFoundException error) {
            Toast.makeText(this, "No browser or Maps app is available. The saved trip stays here.", Toast.LENGTH_LONG).show();
        }
    }

    private void showPlanner(String url) {
        if (isFinishing() || isDestroyed()) return;
        web = new WebView(this);
        WebView.setWebContentsDebuggingEnabled(false);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(false);
        s.setAllowContentAccess(false);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        s.setSupportMultipleWindows(true);
        s.setJavaScriptCanOpenWindowsAutomatically(false);
        CookieManager.getInstance().setAcceptCookie(true);
        CookieManager.getInstance().setAcceptThirdPartyCookies(web, false);
        web.setDownloadListener((a,b,c,d,e) -> Toast.makeText(this,"Downloads open separately from TripPlanner.",Toast.LENGTH_SHORT).show());
        web.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest r) {
                String next = r.getUrl().toString();
                if (internal(next)) return false;
                if (r.isForMainFrame()) external(next);
                return true;
            }
            @Override public WebResourceResponse shouldInterceptRequest(WebView v, WebResourceRequest r) {
                if (internal(r.getUrl().toString())) return null;
                return new WebResourceResponse("text/plain","UTF-8",403,"Blocked",java.util.Collections.emptyMap(),new ByteArrayInputStream(new byte[0]));
            }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override public boolean onCreateWindow(WebView v, boolean dialog, boolean gesture, Message result) {
                if (!gesture) return false;
                WebView popup = new WebView(MainActivity.this);
                popup.setWebViewClient(new WebViewClient() {
                    @Override public boolean shouldOverrideUrlLoading(WebView p, WebResourceRequest r) {
                        String next = r.getUrl().toString();
                        if (internal(next)) web.loadUrl(next); else external(next);
                        p.destroy();
                        return true;
                    }
                });
                ((WebView.WebViewTransport)result.obj).setWebView(popup);
                result.sendToTarget();
                return true;
            }
        });
        FrameLayout content = new FrameLayout(this);
        content.addView(web, new FrameLayout.LayoutParams(-1,-1));
        setContentView(content, new ViewGroup.LayoutParams(-1,-1));
        if (android.os.Build.VERSION.SDK_INT >= 30) {
            content.setOnApplyWindowInsetsListener((v,insets) -> {
                android.graphics.Insets bars = insets.getInsets(android.view.WindowInsets.Type.systemBars());
                v.setPadding(bars.left,bars.top,bars.right,bars.bottom);
                return insets;
            });
            content.requestApplyInsets();
        }
        web.loadUrl(url);
        if (android.os.Build.VERSION.SDK_INT >= 33) {
            backCallback = () -> navigateBack();
            getOnBackInvokedDispatcher().registerOnBackInvokedCallback(
                android.window.OnBackInvokedDispatcher.PRIORITY_DEFAULT, backCallback);
        }
    }

    private void navigateBack() {
        if (web != null && web.canGoBack()) web.goBack(); else finish();
    }
    @Override public void onBackPressed() { navigateBack(); }
    @Override protected void onDestroy() {
        if (android.os.Build.VERSION.SDK_INT >= 33 && backCallback != null) {
            getOnBackInvokedDispatcher().unregisterOnBackInvokedCallback(backCallback);
        }
        if (web != null) { web.stopLoading(); web.destroy(); web = null; }
        // Keep the process service across rotation. Android owns process teardown.
        super.onDestroy();
    }
}
