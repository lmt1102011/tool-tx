package com.lmt.tooltx

import android.os.Bundle
import android.view.View
import androidx.appcompat.app.AppCompatActivity
import androidx.fragment.app.Fragment
import com.google.android.material.bottomnavigation.BottomNavigationView
import com.lmt.tooltx.ui.auth.SignInFragment
import com.lmt.tooltx.ui.auth.SignUpFragment
import com.lmt.tooltx.ui.home.HomeFragment
import com.lmt.tooltx.ui.topup.TopUpFragment
import com.lmt.tooltx.ui.tool.ToolFragment
import com.lmt.tooltx.ui.settings.SettingsFragment
import com.lmt.tooltx.ui.admin.AdminFragment
import com.lmt.tooltx.ui.browser.BrowserFragment
import com.lmt.tooltx.bridge.PythonBridge

class MainActivity : AppCompatActivity() {

    private lateinit var bottomNav: BottomNavigationView
    private val pythonBridge by lazy { PythonBridge(this) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        pythonBridge.setSessionPath(filesDir.absolutePath + "/session.json")

        bottomNav = findViewById(R.id.bottom_nav)
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
    }

    fun showFragment(cls: Class<out Fragment>, tag: String) {
        val fm = supportFragmentManager
        val existing = fm.findFragmentByTag(tag)
        val current = fm.primaryNavigationFragment

        if (existing != null && existing == current) return

        val ft = fm.beginTransaction()
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

        val isAuth = tag == "signin" || tag == "signup"
        bottomNav.visibility = if (isAuth) View.GONE else View.VISIBLE
    }

    fun showNav(show: Boolean) {
        bottomNav.visibility = if (show) View.VISIBLE else View.GONE
    }

    fun showAdmin(show: Boolean) {
        bottomNav.menu.findItem(R.id.nav_admin)?.isVisible = show
    }

    fun openBrowser() {
        showFragment(BrowserFragment::class.java, "browser")
    }

    fun getBridge(): PythonBridge = pythonBridge

    @Suppress("DEPRECATION")
    override fun onBackPressed() {
        val fm = supportFragmentManager
        if (fm.backStackEntryCount > 0) {
            fm.popBackStack()
        } else {
            val current = fm.primaryNavigationFragment
            if (current is SignInFragment || current is SignUpFragment) {
                // Don't exit
            } else {
                showFragment(SignInFragment::class.java, "signin")
            }
        }
    }
}
