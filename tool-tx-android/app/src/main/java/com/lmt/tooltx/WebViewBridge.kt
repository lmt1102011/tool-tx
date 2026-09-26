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
        "var A=window.__txAudio||(window.__txAudio={cxs:[],origPlay:null,origAC:null,patched:0,armed:0,obs:null,timer:null});" +
        "function killA(){var m=document.querySelectorAll('audio,video');var i;for(i=0;i<m.length;i++){try{m[i].muted=true;}catch(_){}}}" +
        "function susp(){if(!A.armed)return;var i;for(i=0;i<(A.cxs||[]).length;i++){try{var c=A.cxs[i];if(c&&c.state!=='suspended'&&c.suspend)c.suspend();}catch(_){}}}" +
        "killA();" +
        "if(!A.origPlay){A.origPlay=HTMLMediaElement.prototype.play;}" +
        "HTMLMediaElement.prototype.play=function(){this.muted=true;return A.origPlay.apply(this,arguments);};" +
        "if(!A.patched){" +
        "A.patched=1;" +
        "var RealAC=A.origAC||window.AudioContext||window.webkitAudioContext;" +
        "if(RealAC&&!A.origAC){A.origAC=RealAC;" +
        "var wAC=function(){var c=new RealAC();A.cxs.push(c);if(A.armed){try{if(c&&c.state!=='suspended'&&c.suspend)c.suspend();}catch(_){}}return c;};" +
        "try{wAC.prototype=RealAC.prototype;}catch(_){}" +
        "window.AudioContext=wAC;if(window.webkitAudioContext)window.webkitAudioContext=wAC;}" +
        "A.obs=new MutationObserver(function(){killA();});" +
        "var root=document.body||document.documentElement;if(root)A.obs.observe(root,{subtree:true,childList:true});" +
        "A.timer=setInterval(function(){killA();susp();},800);" +
        "}else{susp();}" +
        "}catch(e){}})();"

    private val ARM_MUTE_JS = "(function(){try{var A=window.__txAudio;if(!A)return;A.armed=1;var i,m=document.querySelectorAll('audio,video');for(i=0;i<m.length;i++){try{m[i].muted=true;}catch(_){}}for(i=0;i<(A.cxs||[]).length;i++){try{var c=A.cxs[i];if(c&&c.state!=='suspended'&&c.suspend)c.suspend();}catch(_){}}}catch(e){}})();"

    @JvmStatic
    fun armMute() {
        if (!muted) return
        val wv = webView ?: return
        main.postDelayed({
            try { wv.evaluateJavascript(ARM_MUTE_JS, null) } catch (_: Throwable) {}
        }, 4000)
    }

    /** Bật tiếng: gỡ patch play, resume AudioContext đã suspend, unmute media hiện có. */
    private val UNMUTE_JS = "(function(){try{" +
        "var A=window.__txAudio||(window.__txAudio={cxs:[],origPlay:null,origAC:null,patched:0,armed:0,obs:null,timer:null});" +
        "A.patched=0;A.armed=0;" +
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
            "function scan(node,out,depth){" +
            "if(depth>8||!node||typeof node!=='object')return;" +
            "var i,k;" +
            "if(Array.isArray(node)){for(i=0;i<node.length;i++)scan(node[i],out,depth+1);return;}" +
            "var a=node.d1,b=node.d2,c=node.d3;" +
            "if(a!==undefined&&b!==undefined&&c!==undefined&&(a|0)===a&&(b|0)===b&&(c|0)===c&&a>=1&&a<=6&&b>=1&&b<=6&&c>=1&&c<=6){" +
            "out.push(a+b+c+':'+(node.sid===undefined?(node.sidId===undefined?(node.tid===undefined?'':node.tid):node.sidId):node.sid));return;}" +
            "var dc=node.dices||node.dice||node.diceValue||node.d||node.D||node.d123||node.result||node.data;" +
            "if(Array.isArray(dc)&&dc.length>=3&&(dc[0]|0)===dc[0]&&(dc[1]|0)===dc[1]&&(dc[2]|0)===dc[2]&&dc[0]>=1&&dc[0]<=6&&dc[1]>=1&&dc[1]<=6&&dc[2]>=1&&dc[2]<=6){" +
            "out.push((dc[0]+dc[1]+dc[2])+':'+(node.sid===undefined?'':node.sid));return;}" +
            "if(typeof node.sum==='number'&&node.sum>=3&&node.sum<=18){out.push(node.sum+':'+(node.sid===undefined?'':node.sid));return;}" +
            "if(typeof node.Sum==='number'&&node.Sum>=3&&node.Sum<=18){out.push(node.Sum+':'+(node.sid===undefined?'':node.sid));return;}" +
            "if(typeof node.total==='number'&&node.total>=3&&node.total<=18){out.push(node.total+':'+(node.sid===undefined?'':node.sid));return;}" +
            "for(k in node){if(node[k]&&typeof node[k]==='object')scan(node[k],out,depth+1);}" +
            "}" +
            // Quét RIÊNG mệnh lệnh vòng (không phụ thuộc tìm xúc xắc): cmd 1002 = bắt đầu vòng,
            // cmd 1008 = tick kèm tỉ lệ tiền. Nhờ vậy server neo được mốc thời gian THẬT
            // của từng vòng thay vì tự đoán bằng hằng số 18s.
            "function scanCmd(node,depth){" +
            "if(depth>8||!node||typeof node!=='object')return;" +
            "var i,k;" +
            "if(Array.isArray(node)){for(i=0;i<node.length;i++)scanCmd(node[i],depth+1);return;}" +
            "if(node.cmd===1002){window.__rsFlag=1;}" +
            "else if(node.cmd===1008){var g=Array.isArray(node.gi)?node.gi[0]:null;" +
            "if(g&&g.B&&g.S){var tb=Number(g.B.tB),sb=Number(g.S.tB);" +
            "if(isFinite(tb)&&isFinite(sb)&&tb+sb>0)window.__mrFlag=tb/(tb+sb);}}" +
            "for(k in node){if(node[k]&&typeof node[k]==='object')scanCmd(node[k],depth+1);}" +
            "}" +
            // Chống đẩy trùng: onBin thử tối đa 10 offset giải msgpack, mỗi lần gọi emit().
            // Vòng cách nhau 50-90s nên cửa sổ 1s là đủ bỏ hết trùng mà không mất vòng thật.
            "function emit(obj){var out=[],now=Date.now();" +
            "window.__rsFlag=0;window.__mrFlag=0;scanCmd(obj,0);" +
            "if(window.__rsFlag&&now-(window.__lastRsT||0)>1000){window.__lastRsT=now;push({t:now,k:'rs',d:''});}" +
            "if(window.__mrFlag&&now-(window.__lastMrT||0)>1000){window.__lastMrT=now;push({t:now,k:'mr',d:''+window.__mrFlag});}" +
            "scan(obj,out,0);for(var i=0;i<out.length;i++)push({t:now,k:'r',d:out[i]});return out.length;}" +
            "var b,pp;" +
            "function str(n){var s='';var st=pp;var en=pp+n;try{s=String.fromCharCode.apply(null,Array.prototype.slice.call(b.subarray(st,en)));}catch(_){}pp=en;return s;}" +
"function rd(){" +
            "var t=b[pp++],i,j,k,n,o,a,s,l,q,cc,kk;" +
            "if(t===undefined)throw 9;" +
            "if(t<0x80)return t;if(t>0xef)return t-256;" +
            "if(t>=0x80&&t<=0x8f){n=t&15;o={};for(i=0;i<n;i++){k=rd();o[k]=rd();}return o;}" +
            "if(t>=0x90&&t<=0x9f){n=t&15;a=[];for(i=0;i<n;i++)a.push(rd());return a;}" +
            "if(t>=0xa0&&t<=0xbf)return str(t&31);" +
            "if(t>=0xc0&&t<=0xdf){" +
            "if(t===0xc0)return null;if(t===0xc2)return false;if(t===0xc3)return true;" +
            "if(t===0xca){var f=b[pp++]<<24|b[pp++]<<16|b[pp++]<<8|b[pp++];return (new DataView(new Uint8Array([f>>24,f>>16,f>>8,f]).buffer)).getFloat32(0);}" +
            "if(t===0xcb){var f=b[pp++]<<24|b[pp++]<<16|b[pp++]<<8|b[pp++]<<0|b[pp++]<<24|b[pp++]<<16|b[pp++]<<8|b[pp++];return (new DataView(new Uint8Array([f>>24,f>>16,f>>8,f]).buffer)).getFloat64(0);}" +
            "if(t===0xcc)return b[pp++];if(t===0xcd)return (b[pp++]<<8)|b[pp++];if(t===0xce)return ((b[pp++]<<24)|(b[pp++]<<16)|(b[pp++]<<8)|b[pp++])>>>0;" +
            "if(t===0xcf){q=0;for(j=0;j<8;j++)q=q*256+b[pp++];return q;}" +
            "if(t===0xd0)return b[pp++]-256;if(t===0xd1)return ((b[pp++]<<8)|b[pp++])-65536;if(t===0xd2)return ((b[pp++]<<24)|(b[pp++]<<16)|(b[pp++]<<8)|b[pp++])-4294967296;" +
            "if(t===0xd3){q=0;for(j=0;j<8;j++)q=q*256+b[pp++];return q;}" +
            "if(t===0xd9)return str(b[pp++]);" +
            "if(t===0xda){l=(b[pp++]<<8)|b[pp++];}" +
            "else if(t===0xdb){l=(b[pp++]<<24)|(b[pp++]<<16)|(b[pp++]<<8)|b[pp++];}" +
            "if(l!==undefined){s=str(l);return s;}" +
            "if(t===0xc4)l=b[pp++];else if(t===0xc5)l=(b[pp++]<<8)|b[pp++];else if(t===0xc6)l=(b[pp++]<<24)|(b[pp++]<<16)|(b[pp++]<<8)|b[pp++];" +
            "if(l!==undefined){pp+=l;return '';}" +
            "if(t===0xc7){l=b[pp++];pp+=1+l;return '';}" +
            "if(t===0xc8){l=b[pp++]|(b[pp++]<<8)|(b[pp++]<<16)|(b[pp++]<<24);pp+=1+l;return '';}" +
            "if(t===0xc9){l=b[pp++];pp+=1+l;return '';}" +
            "if(t===0xdc){n=(b[pp++]<<8)|b[pp++];a=[];for(i=0;i<n;i++)a.push(rd());return a;}" +
            "if(t===0xdd){q=0;for(j=0;j<4;j++)q=q*256+b[pp++];a=[];for(i=0;i<q;i++)a.push(rd());return a;}" +
            "if(t===0xde){n=(b[pp++]<<8)|b[pp++];o={};for(i=0;i<n;i++){kk=rd();o[kk]=rd();}return o;}" +
            "if(t===0xdf){q=0;for(j=0;j<4;j++)q=q*256+b[pp++];o={};for(i=0;i<q;i++){kk=rd();o[kk]=rd();}return o;}" +
            "throw 9;}" +
            "if(t===0xdc){n=(b[pp++]<<8)|b[pp++];a=[];for(i=0;i<n;i++)a.push(rd());return a;}" +
            "if(t===0xdd){q=0;for(j=0;j<4;j++)q=q*256+b[pp++];a=[];for(i=0;i<q;i++)a.push(rd());return a;}" +
            "if(t===0xde){n=(b[pp++]<<8)|b[pp++];o={};for(i=0;i<n;i++){kk=rd();o[kk]=rd();}return o;}" +
            "if(t===0xdf){q=0;for(j=0;j<4;j++)q=q*256+b[pp++];o={};for(i=0;i<q;i++){kk=rd();o[kk]=rd();}return o;}" +
            "throw 9;}" +
            "function onBin(d){" +
            "try{b=new Uint8Array(d);}catch(_){return;}" +
            "var got=0,st;" +
            "for(st=0;st<10&&st<b.length;st++){" +
            "pp=st;" +
            "try{got=emit(rd());}catch(_){got=0;}" +
            "if(got){return;}" +
            "}" +
            "try{var u8=b.length>120?b.subarray(0,120):b;var hex='';for(var i=0;i<u8.length;i++)hex+=('0'+u8[i].toString(16)).slice(-2);push({t:Date.now(),k:'b',d:hex});}catch(_){}" +
            "}" +
            "function onTxt(d){" +
            "var s=String(d);" +
            "if(s.length>600){s=s.slice(0,600);}" +
            "if(/^4[0123]/.test(s))s=s.slice(2);" +
            "s=s.trim();" +
            "if(s&&(s.charAt(0)==='{'||s.charAt(0)==='[')){" +
            "try{var o=JSON.parse(s);if(emit(o)>0)return;}catch(_){}" +
            "}" +
            "if(s&&s.length<=300)push({t:Date.now(),k:'t',d:s});" +
            "}" +
            "var Orig=window.WebSocket;" +
            "function Wrapped(url,protocols){" +
            "var w=new Orig(url,protocols);" +
            "try{w.binaryType='arraybuffer';}catch(_){}" +
            "try{w.addEventListener('message',function(ev){var d=ev.data;" +
            "if(typeof d==='string'){onTxt(d);}" +
            "else if(d&&d.byteLength!==undefined){onBin(d);}" +
            "else if(d&&d.arrayBuffer){try{d.arrayBuffer().then(function(ab){onBin(ab);}).catch(function(){});}catch(_){}}" +
            "else if(d&&d.data){try{onBin(d.data);}catch(_){}}" +
            "});}catch(_){}" +
            "return w;}" +
            "Wrapped.prototype=Orig.prototype;" +
            "Wrapped.CONNECTING=Orig.CONNECTING;Wrapped.OPEN=Orig.OPEN;Wrapped.CLOSING=Orig.CLOSING;Wrapped.CLOSED=Orig.CLOSED;" +
            "window.WebSocket=Wrapped;" +
            "window.__wsDecode=1;" +
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

    private val GAME_BOOT_JS = "(function(){try{" +
        "var d=document,i,t=0,ids=['mask','handImage','div_full_screen','qrcode'];" +
        "for(i=0;i<ids.length;i++){var e=d.getElementById(ids[i]);if(e){e.style.display='none';e.style.visibility='hidden';}}" +
        "var c=d.getElementById('GameCanvas')||d.getElementById('GameDiv');" +
        "var evs=['touchstart','touchend','touchmove','pointerdown','pointerup','mousedown','mouseup','click','keydown'];" +
        "if(c){try{c.focus&&c.focus();}catch(_){}" +
        "for(i=0;i<evs.length;i++){try{c.dispatchEvent(new Event(evs[i],{bubbles:true,cancelable:true}));}catch(_){}}" +
        "for(i=0;i<evs.length;i++){try{d.dispatchEvent(new Event(evs[i],{bubbles:true,cancelable:true}));}catch(_){}}" +
        "}catch(e){}})();"

    @JvmStatic
    fun unstickGame() {
        val wv = webView ?: return
        try {
            wv.evaluateJavascript(GAME_BOOT_JS, null)
        } catch (_: Throwable) {
            try {
                main.post { wv.evaluateJavascript(GAME_BOOT_JS, null) }
            } catch (_: Throwable) {}
        }
    }

    @JvmStatic
    fun isStuckOnSplash(): Boolean {
        val r = evalJs(
            "(function(){try{var s=document.getElementById('spinner');if(!s)return '0';" +
                "var t=getComputedStyle(s);return (t.display!=='none'&&t.visibility!=='hidden')?'1':'0';}catch(e){return '0';}})()",
            4000
        )
        return r != null && r.replace("\"", "").trim() == "1"
    }

    @JvmStatic
    fun reloadGame() {
        val wv = webView ?: return
        main.post {
            try { wv.reload() } catch (_: Throwable) {}
        }
    }

    private val SW_RESET_JS = "(function(){try{" +
        "if(navigator.serviceWorker&&navigator.serviceWorker.getRegistrations){" +
        "navigator.serviceWorker.getRegistrations().then(function(rs){for(var i=0;i<rs.length;i++){try{rs[i].unregister();}catch(_){}}},function(){});}" +
        "if(window.caches&&window.caches.keys){window.caches.keys().then(function(ks){for(var i=0;i<ks.length;i++){try{window.caches.delete(ks[i]);}catch(_){}}},function(){});}" +
        "}catch(e){}})();"

    @JvmStatic
    fun hardReloadGame() {
        unstickGame()
        val wv = webView ?: return
        try {
            wv.evaluateJavascript(SW_RESET_JS) {
                main.postDelayed({
                    try { wv.reload() } catch (_: Throwable) {}
                }, 1500)
            }
        } catch (_: Throwable) {
            reloadGame()
        }
    }
}