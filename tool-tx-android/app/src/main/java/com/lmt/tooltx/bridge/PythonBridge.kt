package com.lmt.tooltx.bridge

import android.content.Context
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform

class PythonBridge(private val context: Context) {

    init {
        if (!Python.isStarted()) {
            Python.start(AndroidPlatform(context))
        }
    }

    private val py by lazy { Python.getInstance() }

    // ── Auth ──
    fun login(username: String, password: String): Map<String, Any?> {
        return try {
            val result = py.getModule("auth").callAttr("login", username, password)
            mapOf("ok" to true, "uid" to result["uid"].toString(), "data" to parseMap(result["data"]))
        } catch (e: Exception) {
            mapOf("ok" to false, "error" to e.message)
        }
    }

    fun register(username: String, password: String, name: String): Map<String, Any?> {
        return try {
            py.getModule("auth").callAttr("register", username, password, name)
            mapOf("ok" to true)
        } catch (e: Exception) {
            mapOf("ok" to false, "error" to e.message)
        }
    }

    fun logout() {
        try {
            py.getModule("auth").callAttr("logout")
        } catch (_: Exception) {}
    }

    fun getSession(): Map<String, Any?>? {
        return try {
            val s = py.getModule("auth").callAttr("get_session")
            if (s.isNone) null else parseMap(s)
        } catch (_: Exception) {
            null
        }
    }

    fun isLoggedIn(): Boolean {
        return try {
            py.getModule("auth").callAttr("is_logged_in").toBoolean()
        } catch (_: Exception) {
            false
        }
    }

    // ── User Data ──
    fun getUserData(): Map<String, Any?> {
        return try {
            val data = py.getModule("auth").callAttr("user_data")
            parseMap(data)
        } catch (e: Exception) {
            mapOf("error" to e.message)
        }
    }

    fun getPicks(): Int {
        return try {
            py.getModule("fb").callAttr("picks", py.getModule("auth").callAttr("user_data")).toInt()
        } catch (_: Exception) {
            -1
        }
    }

    // ── Socket ──
    fun connectSocket(url: String, token: String) {
        try {
            py.getModule("socket_client").callAttr("connect", url, token)
        } catch (_: Exception) {}
    }

    fun disconnectSocket() {
        try {
            py.getModule("socket_client").callAttr("disconnect")
        } catch (_: Exception) {}
    }

    fun isSocketConnected(): Boolean {
        return try {
            py.getModule("socket_client").callAttr("is_connected").toBoolean()
        } catch (_: Exception) {
            false
        }
    }

    // ── Server ──
    fun discoverServer(): String? {
        return try {
            val url = py.getModule("config").callAttr("discover_server")
            if (url.isNone) null else url.toString()
        } catch (_: Exception) {
            null
        }
    }

    // ── Agent ──
    fun startFork(serverUrl: String, code: String): Boolean {
        return try {
            py.getModule("agent").callAttr("start_fork", serverUrl, code).toBoolean()
        } catch (_: Exception) {
            false
        }
    }

    fun startAgent(serverUrl: String, code: String): Boolean {
        return try {
            py.getModule("agent").callAttr("start_agent", serverUrl, code).toBoolean()
        } catch (_: Exception) {
            false
        }
    }

    fun stopAgent() {
        try {
            py.getModule("agent").callAttr("stop")
        } catch (_: Exception) {}
    }

    fun getAgentPair(serverUrl: String): String? {
        return try {
            val code = py.getModule("socket_client").callAttr("agent_pair", serverUrl)
            if (code.isNone) null else code.toString()
        } catch (_: Exception) {
            null
        }
    }

    // ── Admin ──
    fun listUsers(): Map<String, Any?> {
        return try {
            val users = py.getModule("auth").callAttr("list_users")
            parseMap(users)
        } catch (_: Exception) {
            mapOf()
        }
    }

    fun getRate(): Int {
        return try {
            py.getModule("auth").callAttr("get_rate").toInt()
        } catch (_: Exception) {
            5000
        }
    }

    fun setRate(rate: Int) {
        try {
            py.getModule("auth").callAttr("set_rate", rate)
        } catch (_: Exception) {}
    }

    fun addUser(username: String, password: String, picks: Int) {
        try {
            py.getModule("auth").callAttr("register_with_picks", username, password, "", picks)
        } catch (_: Exception) {}
    }

    fun updateBalance(uid: String, balance: Int) {
        try {
            py.getModule("auth").callAttr("update_balance", uid, balance)
        } catch (_: Exception) {}
    }

    fun updateRole(uid: String, role: String) {
        try {
            py.getModule("auth").callAttr("update_role", uid, role)
        } catch (_: Exception) {}
    }

    fun deleteUser(uid: String) {
        try {
            py.getModule("auth").callAttr("delete_user", uid)
        } catch (_: Exception) {}
    }

    // ── Helper ──
    private fun parseMap(obj: com.chaquo.python.PyObject?): Map<String, Any?> {
        if (obj == null || obj.isNone) return mapOf()
        return try {
            val result = mutableMapOf<String, Any?>()
            val keys = obj.callAttr("keys")
            for (key in keys) {
                result[key.toString()] = obj.callAttr("__getitem__", key)
            }
            result
        } catch (_: Exception) {
            mapOf()
        }
    }
}
