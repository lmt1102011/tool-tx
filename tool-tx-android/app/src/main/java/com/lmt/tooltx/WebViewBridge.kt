package com.lmt.tooltx

import android.os.Handler
import android.os.Looper
import android.webkit.WebView
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicReference

object WebViewBridge {

    @Volatile
    private var webView: WebView? = null

    private val main = Handler(Looper.getMainLooper())

    @JvmStatic
    fun attach(wv: WebView?) {
        webView = wv
    }

    @JvmStatic
    fun detach() {
        webView = null
    }

    @JvmStatic
    fun pauseWebView() {
        val wv = webView ?: return
        main.post {
            try { wv.pauseTimers() } catch (_: Throwable) {}
            try { wv.onPause() } catch (_: Throwable) {}
        }
    }

    @JvmStatic
    fun resumeWebView() {
        val wv = webView ?: return
        main.post {
            try { wv.onResume() } catch (_: Throwable) {}
            try { wv.resumeTimers() } catch (_: Throwable) {}
        }
    }

    @JvmStatic
    fun navigate(url: String) {
        val wv = webView ?: return
        main.post { wv.loadUrl(url) }
    }

    @JvmStatic
    fun currentUrl(): String? {
        val wv = webView ?: return null
        val result = AtomicReference<String?>()
        val latch = CountDownLatch(1)
        main.post {
            try {
                result.set(wv.url)
            } catch (e: Throwable) {
                result.set(null)
            }
            latch.countDown()
        }
        latch.await(3, TimeUnit.SECONDS)
        return result.get()
    }

    @JvmStatic
    fun mutePage() {
        val wv = webView ?: return
        val js = "(function(){try{" +
            "function killA(){document.querySelectorAll('audio,video').forEach(function(a){a.muted=true;});}" +
            "killA();" +
            "var op=HTMLMediaElement.prototype.play;" +
            "HTMLMediaElement.prototype.play=function(){this.muted=true;return op.apply(this,arguments);};" +
            "(function(AC){if(!AC)return;var ctor=function(){var c=new AC();if(c.suspend){c.suspend().catch(function(){});}return c;};ctor.prototype=AC.prototype;window.AudioContext=ctor;window.webkitAudioContext=ctor;})(window.AudioContext||window.webkitAudioContext);" +
            "new MutationObserver(function(){killA();}).observe(document.body,{subtree:true,childList:true});" +
            "}catch(e){}})();"
        main.post {
            try {
                wv.evaluateJavascript(js, null)
            } catch (_: Throwable) {}
        }
    }

    @JvmStatic
    @Throws(Throwable::class)
    fun evalJs(expr: String, timeoutMs: Long): String? {
        val wv = webView ?: return null
        val result = AtomicReference<String?>()
        val latch = CountDownLatch(1)
        main.post {
            try {
                wv.evaluateJavascript(expr) { value ->
                    result.set(value)
                    latch.countDown()
                }
            } catch (e: Throwable) {
                result.set(null)
                latch.countDown()
            }
        }
        if (latch.await(timeoutMs, TimeUnit.MILLISECONDS)) {
            return result.get()
        }
        return null
    }
}