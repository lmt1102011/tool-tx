package com.lmt.tooltx

import android.os.Bundle
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
import com.lmt.tooltx.bridge.PythonBridge

class MainActivity : AppCompatActivity() {

    private lateinit var bottomNav: BottomNavigationView
    private val bridge by lazy { PythonBridge(this) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        bottomNav = findViewById(R.id.bottom_nav)
        bottomNav.setOnItemSelectedListener { item ->
            when (item.itemId) {
                R.id.nav_home -> { showFragment(HomeFragment::class.java, "home"); true }
                R.id.nav_topup -> { showFragment(TopUpFragment::class.java, "topup"); true }
                R.id.nav_tool -> { showFragment(ToolFragment::class.java, "tool"); true }
                R.id.nav_settings -> { showFragment(SettingsFragment::class.java, "settings"); true }
                else -> false
            }
        }

        if (savedInstanceState == null) {
            val session = bridge.getSession()
            if (session != null) {
                showFragment(HomeFragment::class.java, "home")
                bottomNav.menu.findItem(R.id.nav_home).isChecked = true
            } else {
                showFragment(SignInFragment::class.java, "signin")
                bottomNav.visibility = android.view.View.GONE
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
        } else {
            val frag = cls.newInstance()
            ft.add(R.id.fragment_container, frag, tag)
        }
        ft.setPrimaryNavigationFragment(shown ?: fm.findFragmentByTag(tag))
        ft.commitAllowingStateLoss()

        val isAuth = tag == "signin" || tag == "signup"
        bottomNav.visibility = if (isAuth) android.view.View.GONE else android.view.View.VISIBLE
    }

    fun showNav(show: Boolean) {
        bottomNav.visibility = if (show) android.view.View.VISIBLE else android.view.View.GONE
    }

    fun showAdmin(show: Boolean) {
        if (show) {
            bottomNav.menu.add(0, R.id.nav_admin, 4, R.string.nav_admin)
                .setIcon(R.drawable.ic_settings)
        } else {
            bottomNav.menu.removeItem(R.id.nav_admin)
        }
    }

    fun getBridge(): PythonBridge = bridge

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
