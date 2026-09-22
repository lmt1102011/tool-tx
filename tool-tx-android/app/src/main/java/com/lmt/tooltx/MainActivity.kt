package com.lmt.tooltx

import android.content.Context
import android.os.Bundle
import android.view.View
import android.view.ViewGroup
import android.widget.Checkable
import android.widget.ImageView
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.app.AppCompatDelegate
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
        bottomNav.setOnItemSelectedListener { item ->
            when (item.itemId) {
                R.id.nav_home -> { showFragment(HomeFragment::class.java, "home"); animateNavItem(item.itemId); true }
                R.id.nav_topup -> { showFragment(TopUpFragment::class.java, "topup"); animateNavItem(item.itemId); true }
                R.id.nav_tool -> { showFragment(ToolFragment::class.java, "tool"); animateNavItem(item.itemId); true }
                R.id.nav_settings -> { showFragment(SettingsFragment::class.java, "settings"); animateNavItem(item.itemId); true }
                R.id.nav_admin -> { showFragment(AdminFragment::class.java, "admin"); animateNavItem(item.itemId); true }
                else -> false
            }
        }
        bottomNav.menu.findItem(R.id.nav_admin).isVisible = false

        if (savedInstanceState == null) {
            val session = pythonBridge.getSession()
            if (session != null) {
                showFragment(HomeFragment::class.java, "home")
                bottomNav.menu.findItem(R.id.nav_home).isChecked = true
            } else {
                showFragment(SignInFragment::class.java, "signin")
                bottomNav.visibility = View.GONE
            }
        }

        startAutoConnect()
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
        if (id != -1) bottomNav.menu.findItem(id).isChecked = true
    }

    fun showNav(show: Boolean) {
        bottomNav.visibility = if (show) View.VISIBLE else View.GONE
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
                            pythonBridge.connectSocket(url, "")
                        }
                    }
                } catch (_: Exception) {}
                delay(10_000)
            }
        }
    }

    private fun animateNavItem(itemId: Int) {
        bottomNav.post {
            try {
                val menuView = bottomNav.getChildAt(0) as? ViewGroup ?: return@post
                for (i in 0 until menuView.childCount) {
                    val itemView = menuView.getChildAt(i)
                    if (itemView is Checkable && itemView.isChecked) {
                        val icon = findIconView(itemView)
                        if (icon != null) {
                            icon.animate().scaleX(1.22f).scaleY(1.22f)
                                .setDuration(120)
                                .withEndAction {
                                    icon.animate().scaleX(1f).scaleY(1f).setDuration(150).start()
                                }
                                .start()
                        }
                        break
                    }
                }
            } catch (_: Exception) {}
        }
    }

    private fun findIconView(root: View): ImageView? {
        if (root is ImageView) return root
        if (root is ViewGroup) {
            for (i in 0 until root.childCount) {
                val found = findIconView(root.getChildAt(i))
                if (found != null) return found
            }
        }
        return null
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