---
name: god-mobile-awareness
description: "God-level mobile platform awareness: iOS (UIKit vs SwiftUI, UIViewController lifecycle, memory management ARC, Grand Central Dispatch, URLSession, Keychain, push notifications APNS, App Store review guidelines, TestFlight, Xcode instruments), Android (Activity/Fragment lifecycle, Jetpack Compose, Coroutines/Flow, Room, WorkManager, FCM push, Play Store deployment, ProGuard/R8, ADB debugging), React Native (Metro bundler, bridge vs JSI, Hermes engine, Expo vs bare workflow, native modules), Flutter (widget tree, BuildContext, StatefulWidget, BLoC/Riverpod, platform channels, Dart isolates), PWA (service workers, Web App Manifest, install prompt, background sync, push via Web Push API), API design for mobile (pagination, offline-first patterns, delta sync, binary protocols), and mobile-specific security (certificate pinning, root/jailbreak detection, biometric auth, secure storage). Never back down — ship to any platform, debug any crash, and optimize any mobile experience."
license: MIT
metadata:
  version: '1.0'
  category: mobile
---

# god-mobile-awareness

You are a veteran mobile engineer who has shipped apps to billions of devices, debugged midnight crashes from symbolicated logs, and dealt with App Store rejections that blocked quarterly releases. You know every platform quirk, every lifecycle trap, and every security hole that a malicious actor could exploit. You never back down from a crash, a memory leak, or a mysterious Keychain failure. You approach mobile development the same way a pilot approaches a cockpit checklist: methodical, verified, and uncompromising.

---

## Core Philosophy

- **Platform discipline.** iOS and Android are not the same. Do not assume cross-platform abstractions behave identically to native — test on device.
- **Lifecycle is everything.** Most mobile bugs come from misunderstood lifecycle transitions. Internalize every state.
- **Memory kills apps.** Mobile OS will silently terminate apps that use too much memory. Profile with Instruments, not guesses.
- **Offline is the default, not the exception.** Design for connectivity loss from day one.
- **Never back down.** If a crash log exists, find the root cause. Symbolicate the stack trace, reproduce locally, fix it.
- **Zero hallucination.** Platform APIs change with OS versions. Always verify API availability and deprecation status in current platform docs (developer.apple.com, developer.android.com).

---

## iOS Fundamentals

### UIKit vs SwiftUI

**UIKit**: Imperative, event-driven, mature (iOS 2+). Use for: complex custom UI components, apps targeting iOS 13-, apps requiring fine-grained control over layout and animation, camera/video pipelines, custom scroll physics.

**SwiftUI**: Declarative, reactive, state-driven (iOS 13+, fully usable iOS 16+). Use for: new apps targeting iOS 16+, widgets (WidgetKit requires SwiftUI), simpler screens, rapid iteration. Limitations: some APIs only in UIKit (e.g., full UITextView functionality), performance issues with complex lists on older OS.

**Interop**: Use `UIViewRepresentable` to wrap UIKit views in SwiftUI, `UIHostingController` to embed SwiftUI views in UIKit.

```swift
// UIViewRepresentable: wrap UIKit UITextField in SwiftUI
struct UITextFieldRepresentable: UIViewRepresentable {
    @Binding var text: String
    
    func makeUIView(context: Context) -> UITextField {
        let textField = UITextField()
        textField.delegate = context.coordinator
        return textField
    }
    
    func updateUIView(_ uiView: UITextField, context: Context) {
        uiView.text = text
    }
    
    func makeCoordinator() -> Coordinator {
        Coordinator($text)
    }
    
    class Coordinator: NSObject, UITextFieldDelegate {
        var text: Binding<String>
        init(_ text: Binding<String>) { self.text = text }
        func textFieldDidChangeSelection(_ textField: UITextField) {
            text.wrappedValue = textField.text ?? ""
        }
    }
}
```

### UIViewController Lifecycle

```
init → viewDidLoad → viewWillAppear → viewDidAppear
                  ← viewWillDisappear ← viewDidDisappear
```

**viewDidLoad**: Called once when view is loaded into memory. Set up UI, configure views, initial data fetch. Do NOT perform layout-dependent work here (bounds not yet set).

**viewWillAppear/viewDidAppear**: Called every time view becomes visible (including return from pushed VC). Use for: refreshing data, starting animations, registering for notifications.

**viewWillDisappear/viewDidDisappear**: Called every time view disappears. Use for: stopping ongoing work (timers, animations), unregistering notifications, saving state.

**viewWillLayoutSubviews/viewDidLayoutSubviews**: Called when bounds change. Use for layout-dependent calculations.

**Critical trap**: Do NOT start network requests in `viewWillAppear` that you don't cancel in `viewWillDisappear` — VC can appear/disappear rapidly during navigation.

### SwiftUI View Lifecycle

SwiftUI views are value types (structs) — created and destroyed frequently. State management drives re-rendering.

**Property wrappers**:
- `@State`: Local, private mutable state. Source of truth for simple values. Stored in SwiftUI, not in struct.
- `@StateObject`: Create and own an ObservableObject. Lifetime tied to view. Use for ViewModels.
- `@ObservedObject`: Reference to ObservableObject owned elsewhere. Will re-render on `@Published` changes.
- `@EnvironmentObject`: Injected into environment, accessed by any child. Use for app-wide state.
- `@Binding`: Two-way reference to parent's state. Child can read and write parent's `@State`.
- `@Environment`: Read system environment values (colorScheme, locale, dismiss action, etc.).

**task modifier**: Async work tied to view lifetime. Cancelled automatically when view disappears.
```swift
.task {
    await loadData()  // Automatically cancelled on disappear
}
.task(id: userId) {
    await loadUserData(for: userId)  // Re-runs when userId changes
}
```

### Memory Management — ARC

**ARC (Automatic Reference Counting)**: Compiler inserts retain/release calls. Not garbage collection — deterministic.

**Retain cycle**: Object A holds strong reference to B, B holds strong reference to A → neither ever deallocated → memory leak.

```swift
// Classic retain cycle with closure
class ViewController: UIViewController {
    var networkManager = NetworkManager()
    
    func loadData() {
        // WRONG: self captured strongly
        networkManager.fetchData { data in
            self.updateUI(data)  // Retain cycle if networkManager stored in self
        }
        
        // CORRECT: weak capture
        networkManager.fetchData { [weak self] data in
            guard let self = self else { return }
            self.updateUI(data)
        }
        
        // unowned: use ONLY when guaranteed self outlives closure
        // Crash if self is deallocated before closure runs
        networkManager.fetchData { [unowned self] data in
            self.updateUI(data)
        }
    }
    
    deinit {
        // Should always be called for well-managed objects
        print("ViewController deallocated")
    }
}
```

**Detecting leaks**: Xcode Instruments → Leaks instrument (shows leaked objects). Memory Graph Debugger (Debug → Memory Graph) shows reference cycles visually.

---

## iOS Concurrency

### Grand Central Dispatch (GCD)

```swift
// Main queue: UI updates (serial)
DispatchQueue.main.async {
    self.tableView.reloadData()
}

// Global queue: background work (concurrent)
// QoS levels: userInteractive, userInitiated, default, utility, background, unspecified
DispatchQueue.global(qos: .userInitiated).async {
    let result = heavyComputation()
    DispatchQueue.main.async {
        self.label.text = result
    }
}

// Custom serial queue (ordered execution)
let serialQueue = DispatchQueue(label: "com.app.database")
serialQueue.async { /* safe serial access */ }

// Dispatch group: wait for multiple async tasks
let group = DispatchGroup()
group.enter(); fetchUser { group.leave() }
group.enter(); fetchOrders { group.leave() }
group.notify(queue: .main) { 
    // Both tasks complete
}

// DispatchSemaphore: limit concurrency
let semaphore = DispatchSemaphore(value: 3)  // Max 3 concurrent
DispatchQueue.global().async {
    semaphore.wait()
    defer { semaphore.signal() }
    performWork()
}
```

### Swift async/await (Swift 5.5+, iOS 15+)

```swift
// Async function
func fetchUser(id: String) async throws -> User {
    let url = URL(string: "https://api.example.com/users/\(id)")!
    let (data, _) = try await URLSession.shared.data(from: url)
    return try JSONDecoder().decode(User.self, from: data)
}

// Call from synchronous context
Task {
    do {
        let user = try await fetchUser(id: "123")
        // Task runs on cooperative thread pool by default
        await MainActor.run {
            self.nameLabel.text = user.name  // UI update on main thread
        }
    } catch {
        print("Error: \(error)")
    }
}

// TaskGroup: structured concurrency
func fetchAllUsers(ids: [String]) async throws -> [User] {
    try await withThrowingTaskGroup(of: User.self) { group in
        for id in ids {
            group.addTask { try await fetchUser(id: id) }
        }
        return try await group.reduce(into: []) { $0.append($1) }
    }
}

// Actor: data race protection
actor UserCache {
    private var cache: [String: User] = [:]
    
    func get(id: String) -> User? { cache[id] }
    func set(id: String, user: User) { cache[id] = user }
}

// @MainActor: guarantee execution on main thread
@MainActor
class ViewModel: ObservableObject {
    @Published var users: [User] = []
    
    func load() async {
        users = try! await fetchAllUsers(ids: ["1", "2"])
        // @MainActor ensures @Published updates on main thread
    }
}
```

---

## iOS Networking

### URLSession

```swift
// Default configuration: disk-cached, credential-stored
let defaultSession = URLSession(configuration: .default)

// Ephemeral: no cache, no cookies, no credential storage
let privateSession = URLSession(configuration: .ephemeral)

// Background: continues when app is suspended/terminated
let bgConfig = URLSessionConfiguration.background(withIdentifier: "com.app.bg")
let bgSession = URLSession(configuration: bgConfig, delegate: self, delegateQueue: nil)

// Data task (async, Swift 5.5+)
func fetch() async throws -> Data {
    let url = URL(string: "https://api.example.com/data")!
    var request = URLRequest(url: url)
    request.setValue("application/json", forHTTPHeaderField: "Accept")
    request.timeoutInterval = 30
    let (data, response) = try await URLSession.shared.data(for: request)
    guard let httpResponse = response as? HTTPURLResponse,
          (200...299).contains(httpResponse.statusCode) else {
        throw URLError(.badServerResponse)
    }
    return data
}

// Download task (large files)
let (tempURL, _) = try await URLSession.shared.download(from: videoURL)
try FileManager.default.moveItem(at: tempURL, to: destinationURL)
```

### Codable

```swift
struct User: Codable {
    let id: Int
    let firstName: String
    let email: String
    let createdAt: Date
    
    // Map JSON keys to Swift property names
    enum CodingKeys: String, CodingKey {
        case id
        case firstName = "first_name"
        case email
        case createdAt = "created_at"
    }
}

let decoder = JSONDecoder()
decoder.keyDecodingStrategy = .convertFromSnakeCase  // Auto-convert snake_case → camelCase
decoder.dateDecodingStrategy = .iso8601

let user = try decoder.decode(User.self, from: jsonData)

// Custom decoding for non-standard types
struct FlexibleID: Codable {
    let value: String
    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if let intVal = try? container.decode(Int.self) {
            value = String(intVal)
        } else {
            value = try container.decode(String.self)
        }
    }
}
```

---

## iOS Keychain

```swift
import Security

// Store item
func storeToken(_ token: String, for key: String) throws {
    let data = Data(token.utf8)
    let query: [String: Any] = [
        kSecClass as String: kSecClassGenericPassword,
        kSecAttrAccount as String: key,
        kSecValueData as String: data,
        // kSecAttrAccessibleWhenUnlocked: only accessible when device unlocked
        // kSecAttrAccessibleAfterFirstUnlock: survives app background (for background tasks)
        kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly
    ]
    
    let status = SecItemAdd(query as CFDictionary, nil)
    if status == errSecDuplicateItem {
        // Update existing
        let updateQuery: [String: Any] = [kSecClass as String: kSecClassGenericPassword,
                                          kSecAttrAccount as String: key]
        let attrs: [String: Any] = [kSecValueData as String: data]
        SecItemUpdate(updateQuery as CFDictionary, attrs as CFDictionary)
    } else if status != errSecSuccess {
        throw KeychainError.unhandledError(status: status)
    }
}

// Read item
func readToken(for key: String) throws -> String? {
    let query: [String: Any] = [
        kSecClass as String: kSecClassGenericPassword,
        kSecAttrAccount as String: key,
        kSecReturnData as String: true,
        kSecMatchLimit as String: kSecMatchLimitOne
    ]
    var result: AnyObject?
    let status = SecItemCopyMatching(query as CFDictionary, &result)
    guard status == errSecSuccess, let data = result as? Data else { return nil }
    return String(data: data, encoding: .utf8)
}
```

**kSecAttrAccessible options**:
- `kSecAttrAccessibleWhenUnlocked`: Most restrictive — only when unlocked. Correct for user credentials.
- `kSecAttrAccessibleAfterFirstUnlock`: Available after first unlock, persists through lock. Use for background refresh tokens.
- `kSecAttrAccessibleAlways`: Available even when locked (deprecated for new items in iOS 12+).
- `ThisDeviceOnly` suffix: Not backed up to iCloud, not migrated to new device. Use for device-specific keys.

**Keychain App Groups**: Share Keychain items between app and extension using `kSecAttrAccessGroup`.

---

## iOS Push Notifications (APNS)

```swift
// 1. Request permission
UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound, .badge]) { granted, error in
    if granted {
        DispatchQueue.main.async {
            UIApplication.shared.registerForRemoteNotifications()
        }
    }
}

// 2. Receive device token
func application(_ application: UIApplication, 
                 didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
    let token = deviceToken.map { String(format: "%02.2hhx", $0) }.joined()
    // Send token to your server
    sendTokenToServer(token)
}

// APNS payload structure:
// {
//   "aps": {
//     "alert": { "title": "New Message", "body": "You have a new message" },
//     "badge": 5,
//     "sound": "default",
//     "content-available": 1,  // Silent notification for background fetch
//     "mutable-content": 1     // Allows UNNotificationServiceExtension to modify
//   },
//   "custom_key": "custom_value"  // App-specific data
// }
```

**UNNotificationServiceExtension**: Intercepts rich notifications before display. Use to: decrypt payload, download attachments (images/video), modify content. Must complete within ~30 seconds.

**Background fetch**: `content-available: 1` + Background Modes capability. App gets ~30 seconds of background execution. Not guaranteed — iOS throttles based on battery and usage patterns.

---

## iOS Debugging

```bash
# Xcode Instruments
# Time Profiler: CPU hotspots (sample-based, see where time is spent)
# Allocations: memory growth, peak usage, object lifetime
# Leaks: detect retain cycles (real-time)
# Energy Log: CPU, GPU, network, location activity vs battery impact

# LLDB commands in Xcode debugger console
po object          # print object (uses description)
p variable         # print with type info
bt                 # backtrace (stack trace)
frame variable     # show all variables in current frame
frame select 3     # jump to frame 3
thread list        # all threads
thread select 2    # switch to thread 2
expr self.label.text = "Debug"  # modify running app

# Symbolicate crash log
atos -arch arm64 -o MyApp.dSYM/Contents/Resources/DWARF/MyApp -l 0x100000000 0x100abc123
# Or use Xcode: Organizer → Crashes (auto-symbolicated with uploaded dSYM)
```

**dSYM files**: Debug Symbol files. Map binary addresses to source code lines. Must be archived with each build. Upload to App Store Connect for automatic symbolication. Store in CI artifact storage (Bitrise, Fastlane).

---

## Android Fundamentals

### Activity Lifecycle

```
onCreate → onStart → onResume ← (user returns)
           ↑                ↓ (loses focus)
      (brought back)    onPause
           ↑                ↓ (no longer visible)
        onRestart       onStop
                            ↓ (killed or back pressed)
                        onDestroy
```

**Critical**: After `onStop`, Android may kill process. On return, `onCreate` is called again. Use `onSaveInstanceState(Bundle)` to save transient UI state. Use `ViewModel` for data that survives configuration changes.

**Configuration changes** (rotation, locale change): By default, Activity is destroyed and recreated. `ViewModel` survives. `rememberSaveable` (Compose) or `onSaveInstanceState` saves primitive state.

### Jetpack Compose Lifecycle

```kotlin
@Composable
fun MyScreen(viewModel: MyViewModel = viewModel()) {
    // remember: survives recomposition, not configuration change
    var count by remember { mutableStateOf(0) }
    
    // rememberSaveable: survives recomposition AND configuration change
    var inputText by rememberSaveable { mutableStateOf("") }
    
    // LaunchedEffect: runs coroutine, restarts when key changes
    LaunchedEffect(Unit) {  // Unit key = run once on first composition
        viewModel.loadData()
    }
    LaunchedEffect(userId) {  // Restarts when userId changes
        viewModel.loadUser(userId)
    }
    
    // DisposableEffect: cleanup when leaving composition
    DisposableEffect(lifecycle) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) viewModel.refresh()
        }
        lifecycle.addObserver(observer)
        onDispose { lifecycle.removeObserver(observer) }
    }
    
    // SideEffect: runs on every successful recomposition
    SideEffect {
        analytics.track("screen_viewed")
    }
}

// State hoisting: lift state up to parent
@Composable
fun Counter(count: Int, onIncrement: () -> Unit) {  // Stateless, testable
    Button(onClick = onIncrement) { Text("Count: $count") }
}

@Composable
fun CounterScreen() {
    var count by remember { mutableStateOf(0) }
    Counter(count = count, onIncrement = { count++ })
}
```

---

## Android Coroutines and Flow

```kotlin
// ViewModel with coroutines
class UserViewModel : ViewModel() {
    private val _users = MutableStateFlow<List<User>>(emptyList())
    val users: StateFlow<List<User>> = _users.asStateFlow()
    
    init {
        viewModelScope.launch {  // Automatically cancelled when ViewModel cleared
            loadUsers()
        }
    }
    
    private suspend fun loadUsers() {
        // Dispatchers.IO: disk/network (thread pool optimized for blocking I/O)
        // Dispatchers.Default: CPU-intensive (thread pool sized to CPU count)
        // Dispatchers.Main: UI thread
        val result = withContext(Dispatchers.IO) {
            userRepository.fetchUsers()
        }
        _users.value = result
    }
}

// Collect in Compose
@Composable
fun UserList(viewModel: UserViewModel = viewModel()) {
    val users by viewModel.users.collectAsState()
    LazyColumn { items(users) { user -> UserItem(user) } }
}

// Flow: cold stream (starts on collect)
// StateFlow: hot, current state always available, replays last value
// SharedFlow: hot, can replay N values to new subscribers

// coroutineScope vs supervisorScope:
// coroutineScope: child failure cancels parent and siblings
// supervisorScope: child failure does NOT cancel siblings (use for independent work)
suspend fun fetchDashboard() = supervisorScope {
    val users = async { userRepo.fetch() }
    val metrics = async { metricsRepo.fetch() }
    // metrics continues even if users throws
    Dashboard(users.await(), metrics.await())
}
```

---

## Android Persistence

### Room

```kotlin
// Entity
@Entity(tableName = "users")
data class UserEntity(
    @PrimaryKey val id: String,
    val name: String,
    val email: String,
    val createdAt: Long
)

// DAO
@Dao
interface UserDao {
    @Query("SELECT * FROM users WHERE id = :id")
    suspend fun getById(id: String): UserEntity?
    
    @Query("SELECT * FROM users ORDER BY name")
    fun observeAll(): Flow<List<UserEntity>>  // Flow for reactive updates
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(user: UserEntity)
    
    @Delete
    suspend fun delete(user: UserEntity)
    
    @Transaction  // Atomic batch insert
    suspend fun replaceAll(users: List<UserEntity>) {
        deleteAll()
        insertAll(users)
    }
}

// Database
@Database(entities = [UserEntity::class], version = 2)
abstract class AppDatabase : RoomDatabase() {
    abstract fun userDao(): UserDao
    
    companion object {
        val MIGRATION_1_2 = object : Migration(1, 2) {
            override fun migrate(database: SupportSQLiteDatabase) {
                database.execSQL("ALTER TABLE users ADD COLUMN phone TEXT")
            }
        }
    }
}

// Build (use Hilt/Koin for DI)
val db = Room.databaseBuilder(context, AppDatabase::class.java, "app.db")
    .addMigrations(AppDatabase.MIGRATION_1_2)
    .build()
```

### WorkManager

```kotlin
// Define work
class SyncWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result {
        return try {
            val data = inputData.getString("user_id") ?: return Result.failure()
            syncRepository.sync(data)
            Result.success()
        } catch (e: Exception) {
            if (runAttemptCount < 3) Result.retry() else Result.failure()
        }
    }
}

// Enqueue
val constraints = Constraints.Builder()
    .setRequiredNetworkType(NetworkType.CONNECTED)
    .setRequiresCharging(false)
    .build()

val syncRequest = OneTimeWorkRequestBuilder<SyncWorker>()
    .setConstraints(constraints)
    .setInputData(workDataOf("user_id" to userId))
    .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 30, TimeUnit.SECONDS)
    .build()

WorkManager.getInstance(context).enqueue(syncRequest)

// Observe work state
WorkManager.getInstance(context)
    .getWorkInfoByIdLiveData(syncRequest.id)
    .observe(this) { workInfo ->
        when (workInfo?.state) {
            WorkInfo.State.SUCCEEDED -> showSuccess()
            WorkInfo.State.FAILED -> showError()
            else -> {}
        }
    }
```

---

## Android Deployment

```bash
# ADB commands
adb devices                          # List connected devices
adb logcat -v time | grep MyApp     # Filter logs
adb logcat *:E                       # Errors only
adb shell am start -n com.app/.MainActivity  # Launch activity
adb install -r app-debug.apk        # Install (replace existing)
adb uninstall com.example.myapp     # Uninstall
adb shell dumpsys activity activities  # Activity stack
adb bugreport > bugreport.zip       # Full device report
adb shell input tap 500 800         # Simulate tap at coordinates
adb shell monkey -p com.app -v 1000  # Random UI events (stress test)

# ProGuard/R8 rules
# -keep: prevent class/member from being renamed or removed
-keep class com.example.model.** { *; }
-keep class * implements com.google.gson.TypeAdapterFactory
-keepattributes Signature  # Keep generics info for Gson
-keepattributes *Annotation*

# Generate mapping file for de-obfuscating crash reports
# Automatically uploaded to Play Console when AAB is published
```

**AAB vs APK**: Android App Bundle (`.aab`) is the required format for Google Play (since August 2021 for new apps). Play generates device-optimized APKs. Smaller download size (split by ABI, screen density, language). Use `bundletool` to test locally.

---

## React Native

### Metro Bundler

JavaScript bundler for React Native. Config in `metro.config.js`:
```javascript
const { getDefaultConfig } = require('@react-native/metro-config');
const config = getDefaultConfig(__dirname);
// Add custom extensions
config.resolver.sourceExts.push('svg');
// Transformer customization
config.transformer.babelTransformerPath = require.resolve('react-native-svg-transformer');
module.exports = config;
```

### Bridge vs JSI

**Bridge (Legacy Architecture)**: JSON messages serialized/deserialized between JS thread and Native thread. Asynchronous, cannot be synchronous. Serialization overhead for large data.

**JSI (JavaScript Interface — New Architecture)**: Direct memory access between JS engine and native code. Synchronous calls possible. No JSON serialization. TurboModules use JSI (lazy-loaded native modules). Fabric renderer (new UI layer) also uses JSI for direct C++ access.

Enable New Architecture: `RCT_NEW_ARCH_ENABLED=1` in Podfile, `newArchEnabled=true` in `android/gradle.properties`.

### Hermes Engine

AOT JavaScript compiler: compiles JS to bytecode at build time. Reduces startup time, lower memory usage, smaller bundle (bytecode is smaller than JS source). Default since React Native 0.70. Verify in app: `global.HermesInternal !== null`.

### Expo

**Managed workflow**: Expo SDK handles native modules, OTA updates via EAS Update, no Xcode/Android Studio needed for basic development. Limited to Expo SDK modules.

**Bare workflow**: Full native code access. Eject when: need custom native module not in Expo SDK, need specific native configuration. Run: `npx expo eject` (or start bare).

**EAS (Expo Application Services)**: Cloud build service (`eas build`), submission (`eas submit`), OTA updates (`eas update`). Eliminates need for local Xcode/Android Studio for CI.

### Native Modules

```typescript
// TurboModule spec (New Architecture)
// NativeCalculator.ts
import type { TurboModule } from 'react-native';
import { TurboModuleRegistry } from 'react-native';

export interface Spec extends TurboModule {
  add(a: number, b: number): Promise<number>;
}

export default TurboModuleRegistry.getEnforcing<Spec>('Calculator');
```

```kotlin
// Android: RCTCalculatorModule.kt
class CalculatorModule(reactContext: ReactApplicationContext) : 
    NativeCalculatorSpec(reactContext) {
    override fun getName() = "Calculator"
    
    override fun add(a: Double, b: Double, promise: Promise) {
        promise.resolve(a + b)
    }
}
```

---

## Flutter

### Widget Tree

Everything is a widget — layout, styling, interaction, animation. Three types:
1. **StatelessWidget**: Immutable, pure function of inputs. Rebuild when parent rebuilds.
2. **StatefulWidget**: Has mutable `State` object. `setState()` triggers rebuild.
3. **InheritedWidget**: Passes data down tree efficiently (used by `Theme`, `MediaQuery`, `Provider`).

```dart
// StatefulWidget pattern
class Counter extends StatefulWidget {
  const Counter({super.key});
  @override
  State<Counter> createState() => _CounterState();
}

class _CounterState extends State<Counter> {
  int _count = 0;
  
  @override
  void initState() {
    super.initState();
    // Initialize: called once, after widget inserted into tree
  }
  
  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    // Called when InheritedWidget changes (e.g., theme change)
  }
  
  @override
  void didUpdateWidget(Counter oldWidget) {
    super.didUpdateWidget(oldWidget);
    // Called when parent rebuilds with new config
  }
  
  @override
  void dispose() {
    // Clean up: controllers, streams, timers
    super.dispose();
  }
  
  @override
  Widget build(BuildContext context) {
    return Text('$_count');
  }
}
```

### State Management: BLoC

```dart
// Event
abstract class CounterEvent {}
class Increment extends CounterEvent {}

// State
class CounterState {
  final int count;
  const CounterState(this.count);
}

// BLoC
class CounterBloc extends Bloc<CounterEvent, CounterState> {
  CounterBloc() : super(const CounterState(0)) {
    on<Increment>((event, emit) => emit(CounterState(state.count + 1)));
  }
}

// UI
BlocProvider(
  create: (_) => CounterBloc(),
  child: BlocBuilder<CounterBloc, CounterState>(
    builder: (context, state) => Column(children: [
      Text('${state.count}'),
      ElevatedButton(
        onPressed: () => context.read<CounterBloc>().add(Increment()),
        child: const Text('Increment'),
      ),
    ]),
  ),
)
```

### Platform Channels

```dart
// Dart side
const channel = MethodChannel('com.example/native');

Future<String> getBatteryLevel() async {
  try {
    final level = await channel.invokeMethod<int>('getBatteryLevel');
    return '$level%';
  } on PlatformException catch (e) {
    return 'Error: ${e.message}';
  }
}
```

```kotlin
// Android side (in MainActivity.kt)
MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "com.example/native")
    .setMethodCallHandler { call, result ->
        when (call.method) {
            "getBatteryLevel" -> {
                val batteryLevel = getBatteryLevel()
                if (batteryLevel != -1) result.success(batteryLevel)
                else result.error("UNAVAILABLE", "Battery level not available", null)
            }
            else -> result.notImplemented()
        }
    }
```

### Dart Isolates

Dart is single-threaded within an isolate. For CPU-heavy work, spawn an isolate:

```dart
// compute(): simplest isolate spawn (Flutter only)
final result = await compute(heavyJsonParse, jsonString);

// Manual isolate (more control)
import 'dart:isolate';

Future<List<int>> processLargeList(List<int> data) async {
  final receivePort = ReceivePort();
  await Isolate.spawn(_isolateEntry, [receivePort.sendPort, data]);
  return await receivePort.first as List<int>;
}

void _isolateEntry(List<dynamic> args) {
  final sendPort = args[0] as SendPort;
  final data = args[1] as List<int>;
  // CPU-intensive work here, on separate thread
  final result = data.map((n) => n * n).toList();
  sendPort.send(result);
}
```

---

## Progressive Web Apps (PWA)

### Service Worker Lifecycle

```javascript
// Register in main JS
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js')
    .then(reg => console.log('SW registered:', reg.scope))
    .catch(err => console.error('SW registration failed:', err));
}

// sw.js
const CACHE_NAME = 'app-v1';
const PRECACHE_URLS = ['/', '/index.html', '/app.js', '/styles.css'];

// Install: precache critical assets
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(PRECACHE_URLS))
  );
  self.skipWaiting();  // Activate immediately
});

// Activate: clean old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => 
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();  // Take control of open pages immediately
});

// Fetch: serve from cache with network fallback (Cache First)
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request).then(cached => {
      if (cached) return cached;
      return fetch(event.request).then(response => {
        const clone = response.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        return response;
      });
    })
  );
});
```

### Web Push API

```javascript
// Subscribe (client)
const registration = await navigator.serviceWorker.ready;
const subscription = await registration.pushManager.subscribe({
  userVisibleOnly: true,
  applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY)
});
// Send subscription to server for storage

// SW: receive push
self.addEventListener('push', event => {
  const data = event.data?.json();
  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: '/icon-192.png',
      badge: '/badge-72.png',
      data: { url: data.url }
    })
  );
});

// SW: handle notification click
self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil(clients.openWindow(event.notification.data.url));
});
```

**VAPID keys** (Voluntary Application Server Identification): Generate with `web-push generate-vapid-keys`. Server signs push messages with private key, browser verifies with public key.

---

## API Design for Mobile

### Pagination

**Cursor-based** (preferred for mobile):
```json
{
  "data": [...20 items...],
  "cursor": "eyJpZCI6MTAwfQ==",
  "hasMore": true
}
```
Stable under inserts — no skipped or duplicate items. Client sends `?after=<cursor>`.

**Offset-based** (simpler, less stable):
```json
{
  "data": [...20 items...],
  "total": 500,
  "page": 2,
  "pageSize": 20
}
```
Items can shift if new records inserted. Use for admin panels, not feeds.

### Offline-First Patterns

```
Write to local store (immediate UI feedback)
  ↓
Queue operation for sync
  ↓
On connectivity: replay queue to server
  ↓
Resolve conflicts (server wins, client wins, or merge)
```

**Conflict resolution strategies**:
- **Last-Write-Wins (LWW)**: Use server timestamp. Simple, loses concurrent edits.
- **Server-Wins**: Server is authoritative. Safe but frustrating UX.
- **CRDT (Conflict-free Replicated Data Types)**: Math-based merge. Complex but correct. Used by Figma, Notion.

### Delta Sync

```http
# Client sends last-known sync timestamp
GET /api/items?since=2024-01-15T10:00:00Z
If-Modified-Since: Mon, 15 Jan 2024 10:00:00 GMT

# Server responds with only changed items
HTTP/1.1 200 OK
Last-Modified: Mon, 15 Jan 2024 11:30:00 GMT
{
  "items": [...only items changed since 2024-01-15T10:00:00Z...],
  "deletedIds": [101, 102]
}

# Nothing changed
HTTP/1.1 304 Not Modified
```

### Binary Protocols

**Protocol Buffers**: Binary serialization. ~5-10x smaller than equivalent JSON. Schema-first (`.proto` files). gRPC uses Protobuf by default.

```protobuf
syntax = "proto3";
message User {
  string id = 1;
  string name = 2;
  int64 created_at = 3;
}
```

**gRPC on mobile**: iOS with gRPC-Swift, Android with gRPC-Kotlin. Bidirectional streaming. Good for real-time features. HTTP/2 based. Challenge: not native to browser (need gRPC-Web proxy).

---

## Mobile Security

### Certificate Pinning

```swift
// iOS: URLSessionDelegate
class PinningDelegate: NSObject, URLSessionDelegate {
    let pinnedPublicKeyHash = "sha256/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
    
    func urlSession(_ session: URLSession,
                    didReceive challenge: URLAuthenticationChallenge,
                    completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void) {
        guard challenge.protectionSpace.authenticationMethod == NSURLAuthenticationMethodServerTrust,
              let serverTrust = challenge.protectionSpace.serverTrust,
              let certificate = SecTrustGetCertificateAtIndex(serverTrust, 0),
              let publicKey = SecCertificateCopyKey(certificate),
              let publicKeyData = SecKeyCopyExternalRepresentation(publicKey, nil) as Data? else {
            completionHandler(.cancelAuthenticationChallenge, nil)
            return
        }
        let hash = "sha256/" + publicKeyData.sha256Base64()
        if hash == pinnedPublicKeyHash {
            completionHandler(.useCredential, URLCredential(trust: serverTrust))
        } else {
            completionHandler(.cancelAuthenticationChallenge, nil)
        }
    }
}
```

```kotlin
// Android: OkHttp CertificatePinner
val client = OkHttpClient.Builder()
    .certificatePinner(
        CertificatePinner.Builder()
            .add("api.example.com", "sha256/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")
            .add("api.example.com", "sha256/BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB=") // backup pin
            .build()
    )
    .build()
```

**Network Security Config (Android)**: `res/xml/network_security_config.xml` — declarative pinning, custom trust anchors, clear-text traffic restriction. Reference in AndroidManifest: `android:networkSecurityConfig="@xml/network_security_config"`.

### Root/Jailbreak Detection

**Detection approaches** (know these exist but also know they are bypassable):
- iOS: Check for files like `/Applications/Cydia.app`, `/bin/bash`, `/etc/apt`. Check `canOpenURL("cydia://")`. Check if app can write outside sandbox.
- Android: Check for `su` binary in PATH. Check for test keys (`android.os.Build.TAGS.contains("test-keys")`). Use SafetyNet Attestation API (deprecated, use Play Integrity API).

**Play Integrity API** (replacement for SafetyNet):
```kotlin
val integrityManager = IntegrityManagerFactory.create(context)
val request = IntegrityTokenRequest.newBuilder()
    .setNonce(generateNonce())
    .build()
integrityManager.requestIntegrityToken(request)
    .addOnSuccessListener { response ->
        val token = response.token()
        // Send to backend for verification
    }
```

### Biometric Authentication

```swift
// iOS: LocalAuthentication
import LocalAuthentication

let context = LAContext()
var error: NSError?

if context.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: &error) {
    context.evaluatePolicy(.deviceOwnerAuthenticationWithBiometrics,
                           localizedReason: "Authenticate to access your account") { success, error in
        DispatchQueue.main.async {
            if success { showProtectedContent() }
        }
    }
}
```

```kotlin
// Android: BiometricPrompt
val biometricPrompt = BiometricPrompt(this, executor, object : BiometricPrompt.AuthenticationCallback() {
    override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
        // Use result.cryptoObject for crypto operations tied to biometric
        showProtectedContent()
    }
    override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {
        handleError(errString.toString())
    }
})

val promptInfo = BiometricPrompt.PromptInfo.Builder()
    .setTitle("Biometric Authentication")
    .setNegativeButtonText("Cancel")
    .setAllowedAuthenticators(BIOMETRIC_STRONG)
    .build()

biometricPrompt.authenticate(promptInfo)
```

### Secure Storage

| Platform | Mechanism | Notes |
|---|---|---|
| iOS | Keychain | Hardware-backed, use `kSecAttrAccessibleWhenUnlockedThisDeviceOnly` |
| Android 6+ | Android Keystore | Hardware-backed key storage, keys never leave secure element |
| Android (data) | EncryptedSharedPreferences | `MasterKey` + `EncryptedSharedPreferences` from Jetpack Security |
| React Native | react-native-keychain | Wraps iOS Keychain + Android Keystore |
| Flutter | flutter_secure_storage | Wraps iOS Keychain + Android Keystore |

```kotlin
// Android EncryptedSharedPreferences
val masterKey = MasterKey.Builder(context)
    .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
    .build()

val encryptedPrefs = EncryptedSharedPreferences.create(
    context,
    "secure_prefs",
    masterKey,
    EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
    EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
)
encryptedPrefs.edit().putString("auth_token", token).apply()
```

---

## Anti-Hallucination Protocol

1. **iOS API availability**: Always check `@available(iOS X, *)` requirements. APIs added in iOS 16 are not available on iOS 15. Verify on developer.apple.com.
2. **Android API levels**: `minSdk` constraint is real. BiometricPrompt requires API 28+. Verify with `@RequiresApi(Build.VERSION_CODES.P)` and build.gradle `minSdk`.
3. **React Native New Architecture**: Feature flags and module compatibility vary by RN version. Never assume a third-party library supports New Architecture without checking its README.
4. **Expo managed vs bare**: Expo managed has a curated module list. Never suggest a bare native module without noting it requires bare workflow or Expo Config Plugins.
5. **Flutter null safety**: All Flutter code examples must use null-safe Dart (Dart 2.12+, Flutter 2+). Non-null-safe code will not compile.
6. **App Store review**: Guidelines change. Never state a specific capability is "always approved." Reference App Store Review Guidelines and Human Interface Guidelines.
7. **Push notification quotas**: APNS and FCM have rate limits. Never promise delivery guarantees.
8. **Keychain/Keystore behavior**: Hardware security element availability varies by device. Not all Android devices have StrongBox. Check `KeyInfo.isInsideSecureHardware()`.
9. **Service Worker browser support**: PWA features have varying support across browsers. Check caniuse.com for current status.

---

## Self-Review Checklist

Before delivering any mobile implementation, design, or analysis:

- [ ] **Platform target confirmed**: iOS version minimum, Android minSdk specified and APIs verified for that target.
- [ ] **Lifecycle transitions handled**: ViewControllers/Activities not leaking observers, delegates, or timers on disappear/destroy.
- [ ] **Memory management audited**: No strong reference cycles. Closures use `[weak self]`. `deinit`/`onDestroy` confirmed reachable in test.
- [ ] **Main thread safety**: UI updates always on main thread/`@MainActor`/`Dispatchers.Main`. Background work never touches UI directly.
- [ ] **Error handling complete**: Network requests handle timeout, 4xx, 5xx, no-network states. User-facing error messages are non-technical.
- [ ] **Offline scenario tested**: App functions gracefully with no network. Queued writes survive app kill and reconnect.
- [ ] **Keychain/Keystore used for secrets**: No sensitive data in `UserDefaults`/`SharedPreferences`/plain files.
- [ ] **Certificate pinning reviewed**: If implemented, backup pin exists. Rollover plan documented (expiry of pinned cert = app broken).
- [ ] **Background task time limits respected**: iOS background tasks ~30s, WorkManager jobs comply with Doze mode constraints.
- [ ] **Accessibility considered**: VoiceOver/TalkBack labels set on interactive elements. Dynamic type/font scaling tested.
- [ ] **Analytics events verified**: Event names and properties match analytics spec. No PII in event properties.
- [ ] **Build configuration separated**: Debug/Release configs separate. Debug logging disabled in Release. Logging frameworks (CocoaLumberjack, Timber) used, not `print`/`Log.d`.
- [ ] **App Store compliance checked**: No private API usage. Permission strings descriptive and accurate. Data privacy disclosure complete.
- [ ] **Crash reporting integrated**: Firebase Crashlytics or equivalent installed. dSYM/ProGuard mapping uploaded for symbolication.
- [ ] **Performance profiled**: Instruments (iOS) or Android Profiler used on actual device. No jank (missed frames) in critical interactions.
