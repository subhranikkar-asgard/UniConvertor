package com.example.uniconvert.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable

private val UniConvertColorScheme = darkColorScheme(
    primary          = Brand,
    secondary        = Cyan,
    background       = BgDark,
    surface          = SurfaceDark,
    onPrimary        = TextPrimary,
    onSecondary      = TextPrimary,
    onBackground     = TextPrimary,
    onSurface        = TextPrimary,
)

@Composable
fun UniConvertTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = UniConvertColorScheme,
        typography  = Typography,
        content     = content
    )
}
