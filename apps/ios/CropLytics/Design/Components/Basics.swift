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

/// A question, its plain answer, the numbers, and the source line. Rows are separated by hairlines, not cards.
struct AnswerView: View {
    let answer: Answer

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(answer.question)
                .font(.clSecondary)
                .foregroundStyle(Palette.muted)
                .fixedSize(horizontal: false, vertical: true)
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
            if let status = answer.status {
                StatusWord(kind: status.kind, text: status.text)
            }
            if !answer.cite.isEmpty {
                SourceLine(text: answer.cite).padding(.top, 2)
            }
        }
        .padding(.vertical, 12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .accessibilityElement(children: .combine)
        .accessibilityIdentifier("answer-\(answer.id)")
    }
}

/// Answers with hairlines between rows.
struct AnswerList: View {
    let answers: [Answer]
    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            ForEach(Array(answers.enumerated()), id: \.element.id) { i, a in
                if i > 0 { Hairline() }
                AnswerView(answer: a)
            }
        }
    }
}

struct Hairline: View {
    var body: some View { Rectangle().fill(Palette.line).frame(height: 1).accessibilityHidden(true) }
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
        VStack(spacing: 10) {
            Image(systemName: error == .offline ? "wifi.slash" : "exclamationmark.triangle")
                .font(.system(size: 28)).foregroundStyle(Palette.muted)
            Text(error.title).font(.clAnswer).foregroundStyle(Palette.text)
            Text(error.message).font(.clBody).foregroundStyle(Palette.text2).multilineTextAlignment(.center)
            Button("Try again", action: retry).buttonStyle(.tonalPill).accessibilityIdentifier("retry")
        }
        .padding(24)
        .frame(maxWidth: .infinity)
    }
}

/// "Waking the server, up to a minute": the free Render server sleeps when idle.
struct WakingBanner: View {
    var body: some View {
        HStack(spacing: 10) {
            ProgressView().tint(Palette.onAccentContainer)
            VStack(alignment: .leading, spacing: 1) {
                Text("Waking the server, up to a minute").font(.clLabel)
                Text("The free server sleeps when nobody has used it for a while.").font(.clCite).opacity(0.9)
            }
            Spacer(minLength: 0)
        }
        .foregroundStyle(Palette.onAccentContainer)
        .padding(.horizontal, 16).padding(.vertical, 10)
        .background(RoundedRectangle(cornerRadius: Radius.md, style: .continuous).fill(Palette.accentContainer))
        .elevation2()
        .accessibilityElement(children: .combine)
        .accessibilityIdentifier("waking-banner")
    }
}

extension View {
    /// Loading placeholder: the real layout with grey bars while the data loads.
    func placeholder(_ active: Bool) -> some View {
        redacted(reason: active ? .placeholder : [])
            .shimmer(active)
            .disabled(active)
    }

    @ViewBuilder func shimmer(_ active: Bool) -> some View {
        if active { modifier(Shimmer()) } else { self }
    }
}

/// A soft moving highlight over placeholders; still with Reduce Motion.
struct Shimmer: ViewModifier {
    @State private var phase: CGFloat = -1
    @Environment(\.accessibilityReduceMotion) private var reduce
    func body(content: Content) -> some View {
        content.overlay {
            if !reduce {
                GeometryReader { g in
                    LinearGradient(colors: [.clear, Palette.raised.opacity(0.45), .clear], startPoint: .leading, endPoint: .trailing)
                        .frame(width: g.size.width * 0.6)
                        .offset(x: phase * g.size.width)
                }
                .mask(content)
                .allowsHitTesting(false)
                .onAppear { withAnimation(.linear(duration: 1.3).repeatForever(autoreverses: false)) { phase = 1.4 } }
            }
        }
    }
}

/// A label / value row: label muted at the left, value in ink, rows separated by hairlines.
struct FactRow: View {
    let label: String
    let value: String
    var note: String?
    var warn = false
    var body: some View {
        ViewThatFits(in: .horizontal) {
            HStack(alignment: .firstTextBaseline, spacing: 12) {
                Text(label).font(.clSecondary).foregroundStyle(Palette.muted).frame(width: 112, alignment: .leading)
                valueStack
            }
            VStack(alignment: .leading, spacing: 2) {
                Text(label).font(.clSecondary).foregroundStyle(Palette.muted)
                valueStack
            }
        }
        .padding(.vertical, 10)
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

/// A simple wrapping row layout.
struct FlowLayout: Layout {
    var spacing: CGFloat = 8
    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let width = proposal.width ?? .infinity
        var x: CGFloat = 0, y: CGFloat = 0, row: CGFloat = 0, maxX: CGFloat = 0
        for s in subviews {
            let size = s.sizeThatFits(.unspecified)
            if x + size.width > width, x > 0 { x = 0; y += row + spacing; row = 0 }
            x += size.width + spacing; row = max(row, size.height); maxX = max(maxX, x)
        }
        return CGSize(width: min(maxX, width), height: y + row)
    }
    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        var x = bounds.minX, y = bounds.minY, row: CGFloat = 0
        for s in subviews {
            let size = s.sizeThatFits(.unspecified)
            if x + size.width > bounds.maxX, x > bounds.minX { x = bounds.minX; y += row + spacing; row = 0 }
            s.place(at: CGPoint(x: x, y: y), proposal: ProposedViewSize(size))
            x += size.width + spacing; row = max(row, size.height)
        }
    }
}
