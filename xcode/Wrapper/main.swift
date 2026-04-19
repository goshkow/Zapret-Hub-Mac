import AppKit

final class StubAppDelegate: NSObject, NSApplicationDelegate {
    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.terminate(nil)
    }
}

let app = NSApplication.shared
let delegate = StubAppDelegate()
app.delegate = delegate
app.setActivationPolicy(.regular)
app.run()
