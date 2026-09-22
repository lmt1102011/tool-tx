package com.lmt.tooltx

import android.animation.ValueAnimator
import android.content.Context
import android.os.Build
import android.os.Bundle
import android.view.View
import android.view.animation.DecelerateInterpolator
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.app.AppCompatDelegate
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import androidx.fragment.app.Fragment
import com.google.android.material.bottomnavigation.BottomNavigationView
import com.lmt.tooltx.bridge.PythonBridge
import com.lmt.tooltx.ui.admin.AdminFragment
import com.lmt.tooltx.ui.auth.SignInFragment
import com.lmt.tooltx.ui.auth.SignUpFragment
import com.lmt.tooltx.ui.browser.BrowserFragment
import com.lmt.tooltx.ui.home.HomeFragment
import com.lmt.tooltx.ui.settings.SettingsFragment
import com.lmt.tooltx.ui.tool.ToolFragment
import com.lmt.tooltx.ui.topup.TopUpFragment
import java.util.ArrayDeque
import kotlinx.coroutines.GlobalScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

class MainActivity : AppCompatActivity() {

    private lateinit var bottomNav: BottomNavigationView
    private lateinit var navPill: View
    private val pythonBridge by lazy { PythonBridge(this) }
    private val navStack = ArrayDeque<String>()

    override fun onCreate(savedInstanceState: Bundle?) {
        val prefs = getSharedPreferences("settings", Context.MODE_PRIVATE)
        AppCompatDelegate.setDefaultNightMode(
            if (prefs.getBoolean("dark_mode", true)) AppCompatDelegate.MODE_NIGHT_YES
            else AppCompatDelegate.MODE_NIGHT_NO
        )
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        pythonBridge.setSessionPath(filesDir.absolutePath + "/session.json")

        bottomNav = findViewById(R.id.bottom_nav)
        navPill = findViewById(R.id.nav_pill)
        bottomNav.setOnItemSelectedListener { item ->
            when (item.itemId) {
                R.id.nav_home -> { showFragment(HomeFragment::class.java, "home"); true }
                R.id.nav_topup -> { showFragment(TopUpFragment::class.java, "topup"); true }
                R.id.nav_tool -> { showFragment(ToolFragment::class.java, "tool"); true }
                R.id.nav_settings -> { showFragment(SettingsFragment::class.java, "settings"); true }
                R.id.nav_admin -> { showFragment(AdminFragment::class.java, "admin"); true }
                else -> false
            }
        }
        bottomNav.menu.findItem(R.id.nav_admin).isVisible = false

        setupImmersive()

        if (savedInstanceState == null) {
            val session = pythonBridge.getSession()
            if (session != null) {
                showFragment(HomeFragment::class.java, "home")
                bottomNav.menu.findItem(R.id.nav_home).isChecked = true
                positionPill(R.id.nav_home)
            } else {
                showFragment(SignInFragment::class.java, "signin")
                bottomNav.visibility = View.GONE
                navPill.visibility = View.GONE
            }
        }

        startAutoConnect()
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (hasFocus) hideSystemBars()
    }

    private fun setupImmersive() {
        val navWrap = findViewById<View>(R.id.nav_wrap)
        ViewCompat.setOnApplyWindowInsetsListener(navWrap) { v, insets ->
            val bottom = insets.getInsets(WindowInsetsCompat.Type.systemBars()).bottom
            v.setPadding(0, 0, 0, bottom)
            WindowInsetsCompat.CONSUMED
        }
        hideSystemBars()
    }

    private fun hideSystemBars() {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                window.setDecorFitsSystemWindows(false)
                val controller = WindowInsetsControllerCompat(window, window.decorView)
                controller.hide(WindowInsetsCompat.Type.navigationBars())
                controller.systemBarsBehavior =
                    WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
            } else {
                @Suppress("DEPRECATION")
                window.decorView.systemUiVisibility = (
                    View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                        or View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                        or View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                        or View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                    )
            }
        } catch (_: Exception) {}
    }

    fun showFragment(cls: Class<out Fragment>, tag: String) {
        showFragment(cls, tag, push = true)
    }

    fun showFragment(cls: Class<out Fragment>, tag: String, push: Boolean) {
        val fm = supportFragmentManager
        val current = fm.primaryNavigationFragment
        if (current != null && current.tag == tag) return

        val ft = fm.beginTransaction()
            .setReorderingAllowed(true)
            .setCustomAnimations(
                R.anim.nav_enter, R.anim.nav_exit,
                R.anim.nav_enter, R.anim.nav_exit
            )
        if (current != null) {
            ft.hide(current)
        }

        val shown = fm.findFragmentByTag(tag)
        if (shown != null) {
            ft.show(shown)
            ft.setPrimaryNavigationFragment(shown)
        } else {
            val frag = cls.getDeclaredConstructor().newInstance()
            ft.add(R.id.fragment_container, frag, tag)
            ft.setPrimaryNavigationFragment(frag)
        }
        ft.commitAllowingStateLoss()
        fm.executePendingTransactions()

        val isAuth = tag == "signin" || tag == "signup"
        bottomNav.visibility = if (isAuth) View.GONE else View.VISIBLE
        navPill.visibility = if (isAuth) View.GONE else View.VISIBLE
        if (isAuth) {
            if (tag == "signin") {
                navStack.clear()
                navStack.addLast(tag)
            } else {
                navStack.removeAll { it == tag }
                navStack.addLast(tag)
            }
        } else if (push) {
            navStack.removeAll { it == "signin" || it == "signup" }
            navStack.removeAll { it == tag }
            navStack.addLast(tag)
        }
        updateNavSelection(tag)
    }

    private fun updateNavSelection(tag: String) {
        val id = when (tag) {
            "home" -> R.id.nav_home
            "topup" -> R.id.nav_topup
            "tool" -> R.id.nav_tool
            "settings" -> R.id.nav_settings
            "admin" -> R.id.nav_admin
            else -> -1
        }
        if (id != -1) {
            bottomNav.menu.findItem(id).isChecked = true
            animatePill(id)
        }
    }

    fun showNav(show: Boolean) {
        bottomNav.visibility = if (show) View.VISIBLE else View.GONE
        navPill.visibility = if (show) View.VISIBLE else View.GONE
    }

    fun showAdmin(show: Boolean) {
        bottomNav.menu.findItem(R.id.nav_admin)?.isVisible = show
        if (show) bottomNav.menu.findItem(R.id.nav_admin).isEnabled = true
    }

    fun openBrowser() {
        showFragment(BrowserFragment::class.java, "browser")
    }

    private fun startAutoConnect() {
        GlobalScope.launch {
            while (isActive) {
                try {
                    val prefs = getSharedPreferences("settings", Context.MODE_PRIVATE)
                    if (prefs.getBoolean("auto_connect", true) && !pythonBridge.isSocketConnected()) {
                        val url = pythonBridge.discoverServer()
                        if (!url.isNullOrEmpty()) {
                            val token = pythonBridge.getSession()?.get("idToken")?.toString().orEmpty()
                            pythonBridge.connectSocket(url, token)
                        }
                    }
                } catch (_: Exception) {}
                delay(10_000)
            }
        }
    }

    private fun positionPill(itemId: Int) {
        bottomNav.post {
            if (navPill.width <= 0) return@post
            navPill.translationX = targetFor(itemId)
        }
    }

    private fun animatePill(itemId: Int) {
        bottomNav.post {
            if (navPill.width <= 0) return@post
            val target = targetFor(itemId)
            if (navPill.translationX == target) return@post
            val anim = ValueAnimator.ofFloat(navPill.translationX, target).apply {
                duration = 220
                interpolator = DecelerateInterpolator()
                addUpdateListener { a -> navPill.translationX = a.animatedValue as Float }
            }
            anim.start()
        }
    }

    private fun targetFor(itemId: Int): Float {
        val width = bottomNav.width
        val count = visibleNavCount()
        if (width <= 0 || count <= 0) return navPill.translationX
        val colWidth = width.toFloat() / count
        var idx = 0
        for (i in 0 until bottomNav.menu.size()) {
            val item = bottomNav.menu.getItem(i)
            if (!item.isVisible) continue
            if (item.itemId == itemId) break
            idx++
        }
        val center = (idx + 0.5f) * colWidth
        return center - navPill.width / 2f
    }

    private fun visibleNavCount(): Int {
        var c = 0
        for (i in 0 until bottomNav.menu.size()) {
            if (bottomNav.menu.getItem(i).isVisible) c++
        }
        return c
    }

    fun getBridge(): PythonBridge = pythonBridge

    @Suppress("DEPRECATION")
    override fun onBackPressed() {
        val fm = supportFragmentManager
        val current = fm.primaryNavigationFragment
        if (current is SignUpFragment) {
            if (navStack.size > 1) {
                navStack.removeLast()
                val prev = navStack.last
                showFragment(fragmentClassFor(prev), prev, push = false)
            } else {
                moveTaskToBack(true)
            }
            return
        }
        if (current is SignInFragment) {
            moveTaskToBack(true)
            return
        }
        if (navStack.size > 1) {
            navStack.removeLast()
            val prev = navStack.last
            showFragment(fragmentClassFor(prev), prev, push = false)
        } else {
            moveTaskToBack(true)
        }
    }

    private fun fragmentClassFor(tag: String): Class<out Fragment> = when (tag) {
        "home" -> HomeFragment::class.java
        "topup" -> TopUpFragment::class.java
        "tool" -> ToolFragment::class.java
        "settings" -> SettingsFragment::class.java
        "admin" -> AdminFragment::class.java
        "browser" -> BrowserFragment::class.java
        "signin" -> SignInFragment::class.java
        "signup" -> SignUpFragment::class.java
        else -> HomeFragment::class.java
    }
}