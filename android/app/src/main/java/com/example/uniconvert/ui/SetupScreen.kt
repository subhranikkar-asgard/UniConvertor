package com.example.uniconvert.ui

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.slideInVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.blur
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.net.URL

private val BgDark    = Color(0xFF080C18)
private val Surface   = Color(0xFF0D1225)
private val Surface2  = Color(0xFF131A35)
private val Brand     = Color(0xFF6366F1)
private val BrandLight= Color(0xFF818CF8)
private val Cyan      = Color(0xFF06B6D4)
private val TextMain  = Color(0xFFE2E8F0)
private val TextMuted = Color(0xFF94A3B8)
private val GlassBg   = Color(0x990D1225)
private val ErrorRed  = Color(0xFFEF4444)
private val GreenOk   = Color(0xFF22C55E)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SetupScreen(onConnect: (String) -> Unit) {
    val scope  = rememberCoroutineScope()
    val keyboard = LocalSoftwareKeyboardController.current

    var host      by remember { mutableStateOf("192.168.") }
    var port      by remember { mutableStateOf("5000") }
    var testing   by remember { mutableStateOf(false) }
    var errorMsg  by remember { mutableStateOf<String?>(null) }
    var visible   by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) { delay(100); visible = true }

    fun tryConnect() {
        keyboard?.hide()
        if (host.isBlank()) { errorMsg = "Enter the server IP address"; return }
        val url = "http://${host.trim()}:${port.trim()}"
        testing  = true
        errorMsg = null
        scope.launch {
            try {
                withContext(Dispatchers.IO) {
                    val conn = URL("$url/").openConnection()
                    conn.connectTimeout = 5000
                    conn.readTimeout    = 5000
                    conn.connect()
                }
                onConnect(url)
            } catch (e: Exception) {
                errorMsg = "Cannot reach $url\n\nMake sure:\n• Flask is running (python app.py)\n• Your phone & PC are on the same Wi-Fi\n• Firewall allows port ${port.trim()}"
            } finally {
                testing = false
            }
        }
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(BgDark)
            .windowInsetsPadding(WindowInsets.systemBars)
    ) {
        // ── Decorative blurred orbs ──────────────────────────────────────
        Box(
            modifier = Modifier
                .size(300.dp)
                .offset(x = 180.dp, y = (-60).dp)
                .clip(CircleShape)
                .background(Color(0xFF7C3AED).copy(alpha = 0.22f))
                .blur(90.dp)
        )
        Box(
            modifier = Modifier
                .size(220.dp)
                .offset(x = (-60).dp, y = 500.dp)
                .clip(CircleShape)
                .background(Cyan.copy(alpha = 0.18f))
                .blur(80.dp)
        )

        // ── Main content ─────────────────────────────────────────────────
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 28.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            AnimatedVisibility(
                visible = visible,
                enter = fadeIn() + slideInVertically(initialOffsetY = { it / 3 })
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {

                    // ── Logo icon ─────────────────────────────────────────
                    Box(
                        modifier = Modifier
                            .size(80.dp)
                            .clip(RoundedCornerShape(24.dp))
                            .background(
                                Brush.linearGradient(listOf(Brand, Cyan))
                            ),
                        contentAlignment = Alignment.Center
                    ) {
                        Text("⚡", fontSize = 38.sp)
                    }

                    Spacer(Modifier.height(20.dp))

                    // ── Title ─────────────────────────────────────────────
                    Text(
                        "UniConvert",
                        color = TextMain,
                        fontSize = 32.sp,
                        fontWeight = FontWeight.Black,
                        letterSpacing = (-0.5).sp
                    )
                    Text(
                        "File Converter & Compressor",
                        color = TextMuted,
                        fontSize = 14.sp,
                        modifier = Modifier.padding(top = 4.dp)
                    )

                    Spacer(Modifier.height(36.dp))

                    // ── Glass card ────────────────────────────────────────
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(24.dp))
                            .background(GlassBg)
                            .border(
                                width = 1.dp,
                                brush = Brush.linearGradient(
                                    listOf(Brand.copy(alpha = 0.35f), Cyan.copy(alpha = 0.2f))
                                ),
                                shape = RoundedCornerShape(24.dp)
                            )
                            .padding(24.dp)
                    ) {
                        Text(
                            "Connect to Server",
                            color = TextMain,
                            fontWeight = FontWeight.Bold,
                            fontSize = 16.sp
                        )
                        Text(
                            "Enter the IP address of the PC running Flask.",
                            color = TextMuted,
                            fontSize = 12.sp,
                            modifier = Modifier.padding(top = 4.dp, bottom = 20.dp)
                        )

                        // IP field
                        Text("Server IP", color = BrandLight, fontSize = 11.sp,
                            fontWeight = FontWeight.SemiBold,
                            modifier = Modifier.padding(bottom = 6.dp))
                        OutlinedTextField(
                            value = host,
                            onValueChange = { host = it; errorMsg = null },
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(12.dp),
                            singleLine = true,
                            placeholder = { Text("e.g. 192.168.1.5", color = TextMuted, fontSize = 14.sp) },
                            keyboardOptions = KeyboardOptions(
                                keyboardType = KeyboardType.Uri,
                                imeAction = ImeAction.Next
                            ),
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedBorderColor  = Brand,
                                unfocusedBorderColor= Surface2,
                                focusedTextColor    = TextMain,
                                unfocusedTextColor  = TextMain,
                                cursorColor         = Brand,
                                focusedContainerColor   = Surface2,
                                unfocusedContainerColor = Surface2,
                            )
                        )

                        Spacer(Modifier.height(12.dp))

                        // Port field
                        Text("Port", color = BrandLight, fontSize = 11.sp,
                            fontWeight = FontWeight.SemiBold,
                            modifier = Modifier.padding(bottom = 6.dp))
                        OutlinedTextField(
                            value = port,
                            onValueChange = { port = it; errorMsg = null },
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(12.dp),
                            singleLine = true,
                            placeholder = { Text("5000", color = TextMuted, fontSize = 14.sp) },
                            keyboardOptions = KeyboardOptions(
                                keyboardType = KeyboardType.Number,
                                imeAction = ImeAction.Done
                            ),
                            keyboardActions = KeyboardActions(onDone = { tryConnect() }),
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedBorderColor  = Brand,
                                unfocusedBorderColor= Surface2,
                                focusedTextColor    = TextMain,
                                unfocusedTextColor  = TextMain,
                                cursorColor         = Brand,
                                focusedContainerColor   = Surface2,
                                unfocusedContainerColor = Surface2,
                            )
                        )

                        // Error message
                        errorMsg?.let { msg ->
                            Spacer(Modifier.height(12.dp))
                            Box(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .clip(RoundedCornerShape(10.dp))
                                    .background(ErrorRed.copy(alpha = 0.12f))
                                    .border(1.dp, ErrorRed.copy(alpha = 0.4f), RoundedCornerShape(10.dp))
                                    .padding(12.dp)
                            ) {
                                Text(msg, color = ErrorRed, fontSize = 12.sp, lineHeight = 18.sp)
                            }
                        }

                        Spacer(Modifier.height(20.dp))

                        // Connect button
                        Button(
                            onClick = ::tryConnect,
                            enabled = !testing,
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(52.dp),
                            shape = RoundedCornerShape(14.dp),
                            colors = ButtonDefaults.buttonColors(
                                containerColor = Brand,
                                contentColor   = Color.White,
                                disabledContainerColor = Brand.copy(alpha = 0.5f)
                            )
                        ) {
                            if (testing) {
                                CircularProgressIndicator(
                                    modifier = Modifier.size(20.dp),
                                    color = Color.White,
                                    strokeWidth = 2.dp
                                )
                                Spacer(Modifier.width(10.dp))
                                Text("Connecting…", fontWeight = FontWeight.Bold)
                            } else {
                                Text("⚡  Connect to UniConvert",
                                    fontWeight = FontWeight.Bold, fontSize = 15.sp)
                            }
                        }
                    }

                    Spacer(Modifier.height(24.dp))

                    // ── How-to hint ───────────────────────────────────────
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(16.dp))
                            .background(Surface.copy(alpha = 0.7f))
                            .border(1.dp, Surface2, RoundedCornerShape(16.dp))
                            .padding(16.dp)
                    ) {
                        Text("How to find your PC's IP",
                            color = BrandLight, fontWeight = FontWeight.SemiBold, fontSize = 13.sp)
                        Spacer(Modifier.height(8.dp))
                        listOf(
                            "Run  ipconfig  in Windows Command Prompt",
                            "Look for 'IPv4 Address' under your Wi-Fi adapter",
                            "Make sure Flask is running:  python app.py",
                            "Both devices must be on the same Wi-Fi network"
                        ).forEachIndexed { i, step ->
                            Row(modifier = Modifier.padding(vertical = 3.dp)) {
                                Text("${i+1}.", color = Brand, fontSize = 12.sp,
                                    fontWeight = FontWeight.Bold,
                                    modifier = Modifier.width(20.dp))
                                Text(step, color = TextMuted, fontSize = 12.sp, lineHeight = 16.sp)
                            }
                        }
                    }
                }
            }
        }
    }
}
