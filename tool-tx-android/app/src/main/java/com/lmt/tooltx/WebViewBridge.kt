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

    @Volatile
    private var muted = true

    @JvmStatic
    fun isMuted(): Boolean = muted

    @JvmStatic
    fun setMuted(mute: Boolean) {
        muted = mute
        val wv = webView ?: return
        val js = if (mute) MUTE_JS else UNMUTE_JS
        main.post {
            try {
                wv.evaluateJavascript(js, null)
            } catch (_: Throwable) {}
        }
    }

    @JvmStatic
    fun mutePage() = setMuted(true)

    @JvmStatic
    fun unmutePage() = setMuted(false)

    private val MUTE_JS = "(function(){try{" +
        "var A=window.__txAudio||(window.__txAudio={cxs:[],origPlay:null,origAC:null,patched:0,obs:null,timer:null});" +
        "function killA(){var m=document.querySelectorAll('audio,video');var i;for(i=0;i<m.length;i++){try{m[i].muted=true;}catch(_){}}}" +
        "killA();" +
        "if(!A.origPlay){A.origPlay=HTMLMediaElement.prototype.play;}" +
        "HTMLMediaElement.prototype.play=function(){this.muted=true;return A.origPlay.apply(this,arguments);};" +
        "if(!A.patched){" +
        "A.patched=1;" +
        "var RealAC=A.origAC||window.AudioContext||window.webkitAudioContext;" +
        "if(RealAC&&!A.origAC){A.origAC=RealAC;" +
        "var wAC=function(){var c=new RealAC();A.cxs.push(c);try{if(c.suspend)c.suspend();else c.close();}catch(_){}};" +
        "try{wAC.prototype=RealAC.prototype;}catch(_){}" +
        "window.AudioContext=wAC;if(window.webkitAudioContext)window.webkitAudioContext=wAC;}" +
        "A.obs=new MutationObserver(function(){killA();});" +
        "var root=document.body||document.documentElement;if(root)A.obs.observe(root,{subtree:true,childList:true});" +
        "A.timer=setInterval(function(){killA();var i;for(i=0;i<(A.cxs||[]).length;i++){try{var c=A.cxs[i];if(c&&c.state!=='suspended'&&c.suspend)c.suspend();}catch(_){}}},800);" +
        "}else{var i;for(i=0;i<(A.cxs||[]).length;i++){try{var c=A.cxs[i];if(c&&c.state!=='suspended'&&c.suspend)c.suspend();}catch(_){}}}" +
        "}catch(e){}})();"

    /** Bật tiếng: gỡ patch play, resume AudioContext đã suspend, unmute media hiện có. */
    private val UNMUTE_JS = "(function(){try{" +
        "var A=window.__txAudio||(window.__txAudio={cxs:[],origPlay:null,origAC:null,patched:0,obs:null,timer:null});" +
        "A.patched=0;" +
        "if(A.obs){try{A.obs.disconnect();}catch(_){}A.obs=null;}" +
        "if(A.timer){try{clearInterval(A.timer);}catch(_){}A.timer=null;}" +
        "document.querySelectorAll('audio,video').forEach(function(a){a.muted=false;if(a.paused){try{a.play().catch(function(){});}catch(_){}}});" +
        "if(A.origPlay){HTMLMediaElement.prototype.play=A.origPlay;A.origPlay=null;}" +
        "var i;for(i=0;i<(A.cxs||[]).length;i++){try{var c=A.cxs[i];if(c&&c.resume)c.resume();}catch(_){}}" +
        "var RealAC=A.origAC||window.AudioContext||window.webkitAudioContext;" +
        "if(RealAC){var orig=A.origAC||RealAC;var wAC=function(){var c=new RealAC();A.cxs.push(c);return c;};try{wAC.prototype=orig.prototype;}catch(_){}window.AudioContext=wAC;if(window.webkitAudioContext)window.webkitAudioContext=wAC;}" +
        "}catch(e){}})();"

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

    @JvmStatic
    fun installWsShim() {
        val wv = webView ?: return
        val js = "(function(){" +
            "if(window.__wsCapShim)return;window.__wsCapShim=1;" +
            "window.__wsLog=[];window.__wsLogMax=2000;" +
            "function push(e){if(!e)return;if(window.__wsLog.length>=window.__wsLogMax)window.__wsLog.shift();window.__wsLog.push(e);}" +
            "var Orig=window.WebSocket;" +
            "function Wrapped(url,protocols){" +
            "var w=new Orig(url,protocols);" +
            "try{w.binaryType='arraybuffer';}catch(_){}" +
            "try{w.addEventListener('message',function(ev){var d=ev.data;" +
            "if(typeof d==='string'){push({t:Date.now(),k:'t',d:d});}" +
            "else if(d&&d.byteLength!==undefined&&d.byteLength>=0){try{var u8=new Uint8Array(d.slice?d.slice(0,1500):d);var hex='';for(var i=0;i<u8.length;i++)hex+=('0'+u8[i].toString(16)).slice(-2);push({t:Date.now(),k:'b',d:hex});}catch(_){}}" +
            "else if(d&&d.arrayBuffer){try{d.arrayBuffer().then(function(ab){try{var u8=new Uint8Array(ab.slice?ab.slice(0,1500):ab);var hex='';for(var i=0;i<u8.length;i++)hex+=('0'+u8[i].toString(16)).slice(-2);push({t:Date.now(),k:'b',d:hex});}catch(_){}}).catch(function(){});}catch(_){}}" +
            "else if(d&&d.data){try{var dd=new Uint8Array(d.data.slice?d.data.slice(0,1500):d.data);var h2='';for(var i=0;i<dd.length;i++)h2+=('0'+dd[i].toString(16)).slice(-2);push({t:Date.now(),k:'b',d:h2});}catch(_){}}" +
            "});}catch(_){}" +
            "return w;}" +
            "Wrapped.prototype=Orig.prototype;" +
            "Wrapped.CONNECTING=Orig.CONNECTING;Wrapped.OPEN=Orig.OPEN;Wrapped.CLOSING=Orig.CLOSING;Wrapped.CLOSED=Orig.CLOSED;" +
            "window.WebSocket=Wrapped;" +
            "})();"
        // Gọi TRỰC TIẾP (đang ở UI thread trong onPageStarted/onPageFinished) —
        // không qua main.post để shim kịp cài TRƯỚC khi game mở WebSocket.
        try {
            wv.evaluateJavascript(js, null)
        } catch (_: Throwable) {
            try {
                main.post { wv.evaluateJavascript(js, null) }
            } catch (_: Throwable) {}
        }
    }

    @JvmStatic
    fun getWsLog(): String? {
        return evalJs("(function(){try{return JSON.stringify(window.__wsLog||[]);}catch(e){return '[]';}})()", 4000)
    }
}