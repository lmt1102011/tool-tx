package com.lmt.tooltx.ui

import android.content.Context
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.Path
import android.graphics.RectF
import android.util.AttributeSet
import android.view.View
import androidx.core.content.ContextCompat
import com.lmt.tooltx.R
import kotlin.math.asin
import kotlin.math.max
import kotlin.math.sqrt

class NavArchBackgroundView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null
) : View(context, attrs) {

    private val fillPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.FILL
        isDither = true
    }
    private val edgePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        isDither = true
    }
    private val archRect = RectF()
    private val fillPath = Path()
    private val edgePath = Path()

    private val gap = dp(6f)
    private val minClear = dp(3f)

    private var bumpCx = 0f
    private var bumpCy = 0f
    private var bumpR = 0f
    private var flatY = 0f
    private var hasGeom = false
    private var lastValidFlatY = 0f
    private var navWrapRef: View? = null

    init {
        fillPaint.color = ContextCompat.getColor(context, R.color.surfaceContainer)
        edgePaint.color = ContextCompat.getColor(context, R.color.outlineVariant)
        edgePaint.strokeWidth = dp(1f)
    }

    fun bind(circle: View, flatRef: View, navWrap: View) {
        navWrapRef = navWrap
        val l = { v: View ->
            val a = IntArray(2)
            val b = IntArray(2)
            v.getLocationInWindow(a)
            getLocationInWindow(b)
            floatArrayOf(a[0] - b[0] + v.width / 2f, a[1] - b[1] + v.height / 2f)
        }
        val recalc: () -> Unit = {
            if (circle.width > 0 && width > 0 && flatRef.width > 0 && flatRef.height > 0) {
                val navVisible = navWrapRef?.visibility == View.VISIBLE
                if (navVisible) {
                    val c = l(circle)
                    val f = l(flatRef)
                    val r = minOf(circle.width, circle.height) / 2f
                    val cy = c[1]
                    val flat = f[1] - flatRef.height / 2f - dp(3f)
                    lastValidFlatY = flat
                    val dyMax = (r - minClear).coerceAtLeast(1f)
                    val dy = (flat - cy).coerceIn(-dyMax, dyMax)
                    val archR = max(r + gap, sqrt((r + minClear) * (r + minClear) + dy * dy))
                    bumpCx = c[0]
                    bumpCy = cy
                    bumpR = archR
                    flatY = cy + dy
                    hasGeom = true
                    fillPaint.color = ContextCompat.getColor(context, R.color.surfaceContainer)
                    edgePaint.color = ContextCompat.getColor(context, R.color.outlineVariant)
                    edgePaint.strokeWidth = dp(1f)
                    invalidate()
                } else {
                    invalidate()
                }
            }
        }
        circle.addOnLayoutChangeListener { _, _, _, _, _, _, _, _, _ -> recalc() }
        flatRef.addOnLayoutChangeListener { _, _, _, _, _, _, _, _, _ -> recalc() }
        addOnLayoutChangeListener { _, _, _, _, _, _, _, _, _ -> recalc() }
        circle.post { recalc() }
        post { recalc() }
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val w = width.toFloat()
        val h = height.toFloat()
        if (w <= 0f || h <= 0f) return
        val cx: Float
        val cy: Float
        val r: Float
        val flat: Float
        if (hasGeom) {
            cx = bumpCx
            cy = bumpCy
            r = bumpR
            flat = flatY
        } else {
            cx = w / 2f
            cy = h * 0.3f
            r = w * 0.14f
            flat = cy
        }
        val dy = (flat - cy).coerceIn(-r + minClear, r - minClear)
        val half = sqrt((r * r - dy * dy).coerceAtLeast(0f))
        val left = (cx - half).coerceAtLeast(0f)
        val right = (cx + half).coerceAtMost(w)
        val start = Math.toDegrees(asin((dy / r).coerceIn(-1f, 1f).toDouble())).toFloat()
        val sweep = 180f + start * 2f

        archRect.set(cx - r, cy - r, cx + r, cy + r)
        fillPath.reset()
        fillPath.moveTo(0f, flat)
        fillPath.lineTo(left, flat)
        fillPath.arcTo(archRect, 180f - start, sweep)
        fillPath.lineTo(right, flat)
        fillPath.lineTo(w, flat)
        fillPath.lineTo(w, h)
        fillPath.lineTo(0f, h)
        fillPath.close()
        canvas.drawPath(fillPath, fillPaint)

        edgePath.reset()
        edgePath.moveTo(0f, flat)
        edgePath.lineTo(left, flat)
        edgePath.arcTo(archRect, 180f - start, sweep)
        edgePath.lineTo(right, flat)
        edgePath.lineTo(w, flat)
        canvas.drawPath(edgePath, edgePaint)
    }

    private fun dp(v: Float): Float = v * resources.displayMetrics.density
}
