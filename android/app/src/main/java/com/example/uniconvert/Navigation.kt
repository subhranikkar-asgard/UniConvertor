package com.example.uniconvert

import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import com.example.uniconvert.ui.SetupScreen
import com.example.uniconvert.ui.WebViewScreen

/**
 * Simple in-memory nav: if we have a saved server URL go straight to WebView,
 * otherwise show the Setup screen.
 */
@Composable
fun AppNavHost() {
    var serverUrl by remember { mutableStateOf<String?>(null) }

    if (serverUrl == null) {
        SetupScreen(onConnect = { url -> serverUrl = url })
    } else {
        WebViewScreen(
            serverUrl = serverUrl!!,
            onDisconnect = { serverUrl = null }
        )
    }
}
