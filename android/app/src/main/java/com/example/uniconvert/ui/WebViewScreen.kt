package com.example.uniconvert.ui

import android.annotation.SuppressLint
import android.content.Intent
import android.net.Uri
import android.webkit.*
import android.widget.Toast
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView

private val BgDark   = Color(0xFF080C18)
private val NavBar   = Color(0xCC0D1225)
private val Brand    = Color(0xFF6366F1)
private val TextMain = Color(0xFFE2E8F0)
private val TextMuted= Color(0xFF94A3B8)
private val Divider  = Color(0xFF1A2340)

@SuppressLint("SetJavaScriptEnabled")
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun WebViewScreen(serverUrl: String, onDisconnect: () -> Unit) {
    val context = LocalContext.current

    var webView   by remember { mutableStateOf<WebView?>(null) }
    var progress  by remember { mutableStateOf(0) }
    var canGoBack by remember { mutableStateOf(false) }
    var pageTitle by remember { mutableStateOf("UniConvert") }
    var showDisconnectDialog by remember { mutableStateOf(false) }

    // ── File chooser state ────────────────────────────────────────────────
    // Holds the callback given by WebChromeClient.onShowFileChooser()
    var fileCallback by remember { mutableStateOf<ValueCallback<Array<Uri>>?>(null) }

    // Single-file picker (all MIME types so images, PDFs, DOCX all work)
    val filePicker = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.GetContent()
    ) { uri ->
        // Deliver the chosen URI back to the WebView (or null = cancelled)
        fileCallback?.onReceiveValue(if (uri != null) arrayOf(uri) else null)
        fileCallback = null
    }

    // Handle Android back button
    BackHandler(enabled = canGoBack) { webView?.goBack() }

    if (showDisconnectDialog) {
        AlertDialog(
            onDismissRequest = { showDisconnectDialog = false },
            containerColor = Color(0xFF0D1225),
            shape = RoundedCornerShape(20.dp),
            title = { Text("Disconnect?", color = TextMain, fontWeight = FontWeight.Bold) },
            text  = { Text("Return to the server setup screen?", color = TextMuted) },
            confirmButton = {
                TextButton(onClick = { showDisconnectDialog = false; onDisconnect() }) {
                    Text("Disconnect", color = Color(0xFFEF4444), fontWeight = FontWeight.Bold)
                }
            },
            dismissButton = {
                TextButton(onClick = { showDisconnectDialog = false }) {
                    Text("Stay", color = Brand)
                }
            }
        )
    }

    Scaffold(
        containerColor = BgDark,
        topBar = {
            Column {
                TopAppBar(
                    title = {
                        Column {
                            Text(pageTitle, color = TextMain, fontWeight = FontWeight.Bold,
                                fontSize = 15.sp, maxLines = 1)
                            Text(serverUrl, color = TextMuted, fontSize = 10.sp, maxLines = 1)
                        }
                    },
                    navigationIcon = {
                        IconButton(onClick = {
                            if (canGoBack) webView?.goBack() else showDisconnectDialog = true
                        }) {
                            Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back",
                                tint = if (canGoBack) Brand else TextMuted)
                        }
                    },
                    actions = {
                        IconButton(onClick = { webView?.reload() }) {
                            Icon(Icons.Default.Refresh, contentDescription = "Reload", tint = Brand)
                        }
                        IconButton(onClick = { showDisconnectDialog = true }) {
                            Icon(Icons.Default.Close, contentDescription = "Disconnect", tint = TextMuted)
                        }
                    },
                    colors = TopAppBarDefaults.topAppBarColors(containerColor = NavBar)
                )
                if (progress < 100) {
                    LinearProgressIndicator(
                        progress = { progress / 100f },
                        modifier = Modifier.fillMaxWidth().height(2.dp),
                        color = Brand, trackColor = Divider
                    )
                }
            }
        }
    ) { padding ->
        AndroidView(
            modifier = Modifier.fillMaxSize().padding(padding),
            factory = { ctx ->
                WebView(ctx).apply {
                    layoutParams = android.view.ViewGroup.LayoutParams(
                        android.view.ViewGroup.LayoutParams.MATCH_PARENT,
                        android.view.ViewGroup.LayoutParams.MATCH_PARENT
                    )

                    settings.apply {
                        javaScriptEnabled           = true
                        domStorageEnabled            = true
                        allowFileAccess              = true
                        allowContentAccess           = true
                        setSupportZoom(false)
                        useWideViewPort              = true
                        loadWithOverviewMode         = true
                        mixedContentMode             = WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
                        cacheMode                    = WebSettings.LOAD_DEFAULT
                        // Allow file access from URLs so multipart uploads work
                        allowFileAccessFromFileURLs  = true
                        allowUniversalAccessFromFileURLs = true
                    }
                    setBackgroundColor(android.graphics.Color.parseColor("#080C18"))

                    // ── WebViewClient ────────────────────────────────────
                    webViewClient = object : WebViewClient() {
                        override fun onPageFinished(view: WebView?, url: String?) {
                            canGoBack = view?.canGoBack() ?: false
                            pageTitle = view?.title ?: "UniConvert"
                        }
                        override fun shouldOverrideUrlLoading(
                            view: WebView?, request: WebResourceRequest?
                        ): Boolean {
                            val url = request?.url?.toString() ?: return false
                            if (url.startsWith(serverUrl)) return false
                            ctx.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
                            return true
                        }
                        override fun onReceivedError(
                            view: WebView?, request: WebResourceRequest?, error: WebResourceError?
                        ) {
                            if (request?.isForMainFrame == true) {
                                val html = """
                                    <html><body style="background:#080c18;color:#94a3b8;font-family:sans-serif;
                                    display:flex;flex-direction:column;align-items:center;justify-content:center;
                                    height:100vh;text-align:center;padding:24px;box-sizing:border-box;">
                                    <div style="font-size:48px">📡</div>
                                    <h2 style="color:#e2e8f0;margin:16px 0 8px">Connection Lost</h2>
                                    <p>Cannot reach <strong style="color:#818cf8">$serverUrl</strong></p>
                                    <p style="font-size:13px">Make sure Flask is still running on your PC.</p>
                                    </body></html>
                                """.trimIndent()
                                view?.loadDataWithBaseURL(null, html, "text/html", "UTF-8", null)
                            }
                        }
                    }

                    // ── WebChromeClient — critical: handle file picker ───
                    webChromeClient = object : WebChromeClient() {
                        override fun onProgressChanged(view: WebView?, newProgress: Int) {
                            progress = newProgress
                        }
                        override fun onReceivedTitle(view: WebView?, title: String?) {
                            pageTitle = title ?: "UniConvert"
                        }

                        /**
                         * THIS is what makes <input type="file"> work in WebView.
                         * Without this override, tapping the upload zone does nothing.
                         */
                        override fun onShowFileChooser(
                            webView: WebView?,
                            filePathCallback: ValueCallback<Array<Uri>>,
                            fileChooserParams: FileChooserParams?
                        ): Boolean {
                            // Cancel any pending callback first to avoid leaking
                            fileCallback?.onReceiveValue(null)
                            fileCallback = filePathCallback

                            try {
                                // Accept all types so user can pick images, PDF, DOCX, etc.
                                filePicker.launch("*/*")
                            } catch (e: Exception) {
                                fileCallback?.onReceiveValue(null)
                                fileCallback = null
                                Toast.makeText(ctx, "Could not open file picker", Toast.LENGTH_SHORT).show()
                            }
                            return true
                        }
                    }

                    // ── Download listener ────────────────────────────────
                    setDownloadListener { url, _, contentDisposition, mimeType, _ ->
                        try {
                            val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
                            ctx.startActivity(intent)
                        } catch (e: Exception) {
                            Toast.makeText(ctx, "Download: $url", Toast.LENGTH_SHORT).show()
                        }
                    }

                    loadUrl(serverUrl)
                    webView = this
                }
            }
        )
    }
}
