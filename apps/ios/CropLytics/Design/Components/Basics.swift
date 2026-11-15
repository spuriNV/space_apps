import SwiftUI

/// The small source line under an answer: instrument in plain words, scale in miles, status words.
struct SourceLine: View {
    let text: String
    var body: some View {
        Text(text)
            .font(.clCite)
            .foregroundStyle(Palette.muted)
            .fixedSize(horizontal: false, vertical: true)
            .accessibilityLabel("Source: \(text)")
    }
}

/// Slab section heading; sentence case, no eyebrow.
struct SectionHeading: View {
    let text: String
    var body: some View {
        Text(text)
            .font(.clHeading)
            .foregroundStyle(Palette.text)
            .accessibilityAddTraits(.isHeader)
    }
}

/// A question, its plain answer, one line of numbers, and the source line.
struct AnswerView: View {
    let answer: Answer

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(answer.question)
                .font(.clLabel)
                .foregroundStyle(Palette.muted)
            Text(answer.headline)
                .font(.clAnswer)
                .foregroundStyle(answer.tone == .warn ? Palette.warn : Palette.text)
                .fixedSize(horizontal: false, vertical: true)
            if !answer.detail.isEmpty {
                Text(answer.detail)
                    .font(.clBody)
                    .foregroundStyle(Palette.text2)
                    .fixedSize(horizontal: false, vertical: true)
            }
            SourceLine(text: answer.cite)
                .padding(.top, 2)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .accessibilityElement(children: .combine)
        .accessibilityIdentifier("answer-\(answer.id)")
    }
}

/// A plain panel: paper-2 fill, 1px rule, 4pt radius. No glass, no big shadow.
struct Panel<Content: View>: View {
    var padding: CGFloat = 14
    @ViewBuilder let content: Content
    var body: some View {
        VStack(alignment: .leading, spacing: 12) { content }
            .padding(padding)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Palette.panel2, in: RoundedRectangle(cornerRadius: Metrics.radius))
            .overlay(RoundedRectangle(cornerRadius: Metrics.radius).strokeBorder(Palette.lineSoft))
    }
}

/// Hairline between rows.
struct Hairline: View {
    var body: some View { Rectangle().fill(Palette.line).frame(height: 1 / UIScreen.main.scale).accessibilityHidden(true) }
}

/// "Saved on 14 Nov 2026": shown when the screen is showing the copy saved on the phone.
struct SavedNote: View {
    let freshness: Freshness?
    var body: some View {
        if let f = freshness, let date = f.savedAt {
            Label {
                Text(f.refreshError == nil
                     ? "Saved on \(GrowerDate.short(date)). Checking for newer data."
                     : "Saved on \(GrowerDate.short(date)). \(f.refreshError == .offline ? "You're offline" : "Can't reach the server right now"), so this is what you saw last time.")
                    .font(.clCite)
            } icon: {
                Image(systemName: "clock.arrow.circlepath").imageScale(.small)
            }
            .foregroundStyle(Palette.muted)
            .accessibilityIdentifier("saved-note")
        }
    }
}

/// Error with a retry button.
struct ErrorStateView: View {
    let error: AppError
    let retry: () -> Void
    var body: some View {
        ContentUnavailableView {
            Label(error.title, systemImage: error == .offline ? "wifi.slash" : "exclamationmark.triangle")
        } description: {
            Text(error.message)
        } actions: {
            Button("Try again", action: retry)
                .buttonStyle(.borderedProminent)
                .accessibilityIdentifier("retry")
        }
        .frame(maxWidth: .infinity, minHeight: 320)
    }
}

/// "Waking the server, up to a minute": the free Render server sleeps when idle.
struct WakingBannerModifier: ViewModifier {
    @Environment(AppEnvironment.self) private var env

    func body(content: Content) -> some View {
        content.safeAreaInset(edge: .top, spacing: 0) {
            if env.serverStatus.isWaking {
                HStack(spacing: 10) {
                    ProgressView().tint(Palette.accentInk)
                    VStack(alignment: .leading, spacing: 1) {
                        Text("Waking the server, up to a minute")
                            .font(.clLabel)
                        Text("The free server sleeps when nobody has used it for a while.")
                            .font(.clCite)
                            .opacity(0.9)
                    }
                    Spacer(minLength: 0)
                }
                .foregroundStyle(Palette.accentInk)
                .padding(.horizontal, Metrics.gutter)
                .padding(.vertical, 10)
                .background(Palette.accent)
                .transition(.move(edge: .top).combined(with: .opacity))
                .accessibilityElement(children: .combine)
                .accessibilityIdentifier("waking-banner")
            }
        }
        .animation(.easeInOut(duration: 0.25), value: env.serverStatus.isWaking)
    }
}

extension View {
    func wakingBanner() -> some View { modifier(WakingBannerModifier()) }

    /// Loading placeholder: the layout with grey bars, while the real data loads.
    func placeholder(_ active: Bool) -> some View {
        redacted(reason: active ? .placeholder : [])
            .disabled(active)
            .accessibilityLabel(active ? Text("Loading") : Text(""))
    }
}

/// "More detail": everything a farmer doesn't need to decide, collapsed (PLAN.md, farmer-first default).
struct MoreDetail<Content: View>: View {
    @State private var expanded = false
    @ViewBuilder let content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            Hairline()
            DisclosureGroup(isExpanded: $expanded) {
                VStack(alignment: .leading, spacing: 22) { content }
                    .padding(.top, 12)
            } label: {
                Text("More detail")
                    .font(.clHeading)
                    .foregroundStyle(Palette.text)
                    .padding(.vertical, 10)
            }
            .accessibilityIdentifier("more-detail")
            .accessibilityHint("Data sources, satellite details and checks")
        }
    }
}

/// A label / value row: label muted at the left, value in ink.
struct FactRow: View {
    let label: String
    let value: String
    var note: String?
    var warn = false
    var body: some View {
        ViewThatFits(in: .horizontal) {
            HStack(alignment: .firstTextBaseline, spacing: 12) {
                Text(label).font(.clSecondary).foregroundStyle(Palette.muted).frame(width: 110, alignment: .leading)
                valueStack
            }
            VStack(alignment: .leading, spacing: 2) {
                Text(label).font(.clSecondary).foregroundStyle(Palette.muted)
                valueStack
            }
        }
        .accessibilityElement(children: .combine)
    }

    private var valueStack: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(value).font(.clBody).foregroundStyle(warn ? Palette.warn : Palette.text)
                .fixedSize(horizontal: false, vertical: true)
            if let note { SourceLine(text: note) }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}
