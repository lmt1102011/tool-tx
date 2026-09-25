package com.lmt.tooltx

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import androidx.core.content.FileProvider
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject

object AppUpdater {

    private const val REPO = "lmt1102011/tool-tx"
    private const val API_LATEST = "https://api.github.com/repos/$REPO/releases/latest"
    private const val API_RELEASES = "https://api.github.com/repos/$REPO/releases?per_page=10"
    private const val PREFS = "tooltx_update"
    private const val KEY_PENDING = "pending_version_code"
    private const val KEY_SEEN = "seen_version"

    data class Release(
        val tag: String,
        val versionName: String,
        val notes: String,
        val assetUrl: String?,
        val assetName: String?,
        val size: Long
    ) {
        val version: List<Int>
            get() = versionName.split('.').map { it.trim().toIntOrNull() ?: 0 }
    }

    fun versionName(context: Context): String {
        val p = context.packageManager.getPackageInfo(context.packageName, 0)
        return p.versionName ?: "0.0.0"
    }

    fun versionCode(context: Context): Long {
        val p = context.packageManager.getPackageInfo(context.packageName, 0)
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) p.longVersionCode
        else @Suppress("DEPRECATION") p.versionCode.toLong()
    }

    private fun newerThanCurrent(parts: List<Int>, current: List<Int>): Boolean {
        val n = maxOf(parts.size, current.size)
        for (i in 0 until n) {
            val a = parts.getOrElse(i) { 0 }
            val b = current.getOrElse(i) { 0 }
            if (a != b) return a > b
        }
        return false
    }

    private fun parseVersion(raw: String): String =
        raw.trim().removePrefix("v").substringBefore(' ').trim()

    private fun parseRelease(obj: JSONObject): Release? {
        val tag = obj.optString("tag_name").trim()
        if (tag.isEmpty() || obj.optBoolean("draft", false)) return null
        val assets = obj.optJSONArray("assets")
        var url: String? = null
        var name: String? = null
        var size = 0L
        if (assets != null) {
            for (i in 0 until assets.length()) {
                val a = assets.optJSONObject(i) ?: continue
                val an = a.optString("name")
                if (an.endsWith(".apk", true)) {
                    url = a.optString("browser_download_url").takeIf { it.isNotEmpty() }
                    name = an
                    size = a.optLong("size", 0L)
                    break
                }
            }
        }
        return Release(
            tag = tag,
            versionName = parseVersion(tag),
            notes = obj.optString("body").trim(),
            assetUrl = url,
            assetName = name,
            size = size
        )
    }

    private fun getJson(url: String): List<JSONObject> = withContext(Dispatchers.IO) {
        val conn = URL(url).openConnection() as HttpURLConnection
        conn.connectTimeout = 15000
        conn.readTimeout = 15000
        conn.setRequestProperty("Accept", "application/vnd.github+json")
        conn.setRequestProperty("User-Agent", "tool-tx-android")
        try {
            val code = conn.responseCode
            val stream = if (code in 200..299) conn.inputStream else conn.errorStream
            val body = stream?.bufferedReader()?.use { it.readText() }.orEmpty()
            if (code !in 200..299) emptyList()
            else if (body.trimStart().startsWith("[")) {
                val arr = org.json.JSONArray(body)
                (0 until arr.length()).mapNotNull { arr.optJSONObject(it) }
            } else {
                listOf(JSONObject(body))
            }
        } finally {
            conn.disconnect()
        }
    }

    private fun currentParts(context: Context) = versionName(context).split('.')
        .map { it.trim().toIntOrNull() ?: 0 }

    suspend fun check(context: Context, force: Boolean = false): Release? {
        val current = currentParts(context)
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        if (!force) {
            val seen = prefs.getString(KEY_SEEN, null)
            if (seen != null && !newerThanCurrent(parseVersion(seen).split('.').map {
                    it.trim().toIntOrNull() ?: 0
                }, current)) return null
        }
        val objects = runCatching {
            getJson(API_LATEST) + getJson(API_RELEASES)
        }.getOrDefault(emptyList())
        var best: Release? = null
        for (obj in objects) {
            val r = parseRelease(obj) ?: continue
            if (r.assetUrl == null) continue
            if (!newerThanCurrent(r.version, current)) continue
            if (best == null || newerThanCurrent(r.version, best.version)) best = r
        }
        return best
    }

    fun markSeen(context: Context, versionName: String) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putString(KEY_SEEN, versionName).apply()
    }

    suspend fun download(
        context: Context,
        release: Release,
        onProgress: suspend (percent: Int, downloaded: Long, total: Long) -> Unit
    ): File = withContext(Dispatchers.IO) {
        val dir = File(context.cacheDir, "apk").apply { mkdirs() }
        val target = File(dir, "tooltx-${release.versionName}.apk")
        val tmp = File(dir, target.name + ".part")
        val conn = URL(release.assetUrl!!).openConnection() as HttpURLConnection
        conn.connectTimeout = 20000
        conn.readTimeout = 30000
        conn.setRequestProperty("User-Agent", "tool-tx-android")
        conn.setRequestProperty("Accept", "application/octet-stream")
        conn.followRedirects = true
        try {
            val code = conn.responseCode
            if (code !in 200..299) throw RuntimeException("HTTP $code")
            val total = conn.contentLength.toLong().takeIf { it > 0 } ?: release.size
            var done = 0L
            var lastPercent = -1
            conn.inputStream.use { input ->
                tmp.outputStream().use { out ->
                    val buf = ByteArray(64 * 1024)
                    while (true) {
                        val n = input.read(buf)
                        if (n < 0) break
                        out.write(buf, 0, n)
                        done += n
                        if (total > 0) {
                            val percent = ((done * 100) / total).toInt()
                            if (percent != lastPercent) {
                                lastPercent = percent
                                onProgress(percent, done, total)
                            }
                        }
                    }
                }
            }
            if (target.exists()) target.delete()
            if (!tmp.renameTo(target)) throw RuntimeException("Không lưu được file APK")
            onProgress(100, done, total)
            target
        } finally {
            conn.disconnect()
        }
    }

    fun install(context: Context, apk: File) {
        val uri: Uri = FileProvider.getUriForFile(context, context.packageName + ".fileprovider", apk)
        val intent = Intent(Intent.ACTION_INSTALL_PACKAGE).apply {
            setDataAndType(uri, "application/vnd.android.package-archive")
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putLong(KEY_PENDING, versionCode(context) + 1).apply()
        context.startActivity(intent)
    }

    fun pendingUpdateDone(context: Context): Boolean {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val pending = prefs.getLong(KEY_PENDING, 0L)
        if (pending <= 0L) return false
        if (versionCode(context) >= pending) {
            prefs.edit().remove(KEY_PENDING).apply()
            return true
        }
        return false
    }
}
