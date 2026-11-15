import SwiftUI

// Controls from docs/ui-redesign-spec.md §4: rounded where you touch it, square where you read it.
// Every control: 44pt target, a pressed state layer, a disabled look; selection is a tonal fill, never a green slab.

/// Pill buttons: one primary per panel (filled green), tonal secondaries, neutral outline, and text buttons.
struct PillButtonStyle: ButtonStyle {
    enum Kind { case primary, tonal, outline, text }
    var kind: Kind = .tonal
    var small = false
    var fullWidth = false
    @Environment(\.isEnabled) private var enabled
    @Environment(\.accessibilityReduceMotion) private var reduce

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(small ? .clLabel : .clBodyStrong)
            .lineLimit(1)
            .padding(.horizontal, kind == .text ? 12 : (small ? 16 : 20))
            .frame(minHeight: small ? 36 : 44)
            .frame(maxWidth: fullWidth ? .infinity : nil)
            .foregroundStyle(foreground)
            .background(background(configuration.isPressed), in: Capsule())
            .overlay(Capsule().strokeBorder(kind == .outline ? (enabled ? Palette.outline : Palette.line) : .clear, lineWidth: 1))
            .contentShape(Capsule().inset(by: small ? -4 : 0))
            .scaleEffect(configuration.isPressed && !reduce ? 0.98 : 1)
            .animation(Motion.std(reduce, 0.12), value: configuration.isPressed)
    }

    private var foreground: Color {
        guard enabled else { return Palette.muted }
        switch kind {
        case .primary: return Palette.accentInk
        case .tonal: return Palette.onAccentContainer
        case .outline: return Palette.text
        case .text: return Palette.accent
        }
    }

    private func background(_ pressed: Bool) -> AnyShapeStyle {
        guard enabled else { return AnyShapeStyle(kind == .text || kind == .outline ? Color.clear : Palette.stateStrong) }
        switch kind {
        case .primary: return AnyShapeStyle(pressed ? Palette.accentPressed : Palette.accent)
        case .tonal: return AnyShapeStyle(pressed ? Palette.accentContainerHover : Palette.accentContainer)
        case .outline, .text: return AnyShapeStyle(pressed ? Palette.statePressed : Color.clear)
        }
    }
}

extension ButtonStyle where Self == PillButtonStyle {
    static var primaryPill: PillButtonStyle { PillButtonStyle(kind: .primary) }
    static var tonalPill: PillButtonStyle { PillButtonStyle(kind: .tonal) }
    static var outlinePill: PillButtonStyle { PillButtonStyle(kind: .outline) }
    static var textPill: PillButtonStyle { PillButtonStyle(kind: .text) }
    static func pill(_ kind: PillButtonStyle.Kind, small: Bool = false, fullWidth: Bool = false) -> PillButtonStyle {
        PillButtonStyle(kind: kind, small: small, fullWidth: fullWidth)
    }
}

/// Round icon button: 40pt disc (a visible neutral disc so Close is findable), 44pt hit area.
struct IconButton: View {
    let systemName: String
    let label: String
    var ghost = false
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Image(systemName: systemName)
                .font(.system(size: 17, weight: .semibold))
                .frame(width: 40, height: 40)
        }
        .buttonStyle(IconButtonStyle(ghost: ghost))
        .frame(width: 44, height: 44)
        .contentShape(Circle())
        .accessibilityLabel(label)
    }
}

struct IconButtonStyle: ButtonStyle {
    var ghost = false
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .foregroundStyle(Palette.text2)
            .background(Circle().fill(configuration.isPressed ? Palette.stateStrong : (ghost ? Color.clear : Palette.stateHover)))
    }
}

/// Filter chip: outlined off; tonal container with a check when on (three cues, not colour alone).
struct FilterChip: View {
    let title: String
    var count: Int?
    let isOn: Bool
    let action: () -> Void
    @Environment(\.accessibilityReduceMotion) private var reduce

    var body: some View {
        Button(action: action) {
            HStack(spacing: 6) {
                if isOn {
                    Image(systemName: "checkmark").font(.system(size: 13, weight: .bold))
                        .foregroundStyle(Palette.accentOutline)
                        .transition(.scale.combined(with: .opacity))
                }
                Text(title).font(.clLabel)
                if let count { Text("\(count)").font(.clSecondary).foregroundStyle(isOn ? Palette.onAccentContainer : Palette.muted) }
            }
            .lineLimit(1)
            .fixedSize()
            .padding(.leading, isOn ? 12 : 16)
            .padding(.trailing, 16)
            .frame(height: 36)
            .foregroundStyle(isOn ? Palette.onAccentContainer : Palette.text2)
            .background(Capsule().fill(isOn ? Palette.accentContainer : Color.clear))
            .overlay(Capsule().strokeBorder(isOn ? Color.clear : Palette.outline, lineWidth: 1))
            .padding(.vertical, 4)
            .contentShape(Capsule())
        }
        .buttonStyle(StateLayerStyle(shape: Capsule()))
        .animation(Motion.std(reduce), value: isOn)
        .accessibilityAddTraits(isOn ? .isSelected : [])
    }
}

/// Plain pressed state layer for rows and chips.
struct StateLayerStyle<S: Shape>: ButtonStyle {
    var shape: S
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .overlay(shape.fill(configuration.isPressed ? Palette.statePressed : .clear).allowsHitTesting(false))
    }
}

/// Segmented control: a raised paper thumb on a sunken track, never a green fill. Radio semantics for VoiceOver.
struct PillSegmented<Value: Hashable>: View {
    let label: String
    let options: [(value: Value, title: String)]
    @Binding var selection: Value
    var disabled: Set<Value> = []
    @Namespace private var ns
    @Environment(\.accessibilityReduceMotion) private var reduce

    var body: some View {
        HStack(spacing: 2) {
            ForEach(options, id: \.value) { option in
                let on = option.value == selection
                Button {
                    withAnimation(Motion.std(reduce)) { selection = option.value }
                } label: {
                    Text(option.title)
                        .font(.clLabel)
                        .lineLimit(1)
                        .minimumScaleFactor(0.8)
                        .padding(.horizontal, 12)
                        .frame(maxWidth: .infinity, minHeight: 34)
                        .foregroundStyle(on ? Palette.text : Palette.text2)
                        .background {
                            if on {
                                Capsule().fill(Palette.raised).elevation1()
                                    .overlay(Capsule().strokeBorder(Palette.lineSoft))
                                    .matchedGeometryEffect(id: "thumb", in: ns)
                            }
                        }
                        .contentShape(Capsule())
                }
                .buttonStyle(.plain)
                .disabled(disabled.contains(option.value))
                .opacity(disabled.contains(option.value) ? 0.6 : 1)
                .accessibilityLabel(option.title)
                .accessibilityAddTraits(on ? [.isSelected, .isButton] : .isButton)
            }
        }
        .padding(3)
        .frame(minHeight: 40)
        .background(Capsule().fill(Palette.panel2))
        .overlay(Capsule().strokeBorder(Palette.lineSoft))
        .accessibilityElement(children: .contain)
        .accessibilityLabel(label)
    }
}

/// Section heading without a rule; optional trailing text action.
struct SectionHeader<Trailing: View>: View {
    let title: String
    @ViewBuilder var trailing: Trailing

    var body: some View {
        HStack(alignment: .firstTextBaseline, spacing: 12) {
            Text(title).font(.clHeading).foregroundStyle(Palette.text)
                .fixedSize(horizontal: false, vertical: true)
                .accessibilityAddTraits(.isHeader)
            Spacer(minLength: 0)
            trailing
        }
        .padding(.top, 8)
    }
}

extension SectionHeader where Trailing == EmptyView {
    init(_ title: String) { self.title = title; self.trailing = EmptyView() }
}

/// The app-wide "More detail" switch (§4.8): a sunken row, chevron rotates, label flips to "Less detail".
struct MoreDetailRow: View {
    let teaser: String
    @Environment(AppModel.self) private var app
    @Environment(\.accessibilityReduceMotion) private var reduce

    var body: some View {
        Button {
            withAnimation(Motion.std(reduce, 0.24)) { app.detailOn.toggle() }
        } label: {
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text(app.detailOn ? "Less detail" : "More detail").font(.clBodyBold).foregroundStyle(Palette.accent)
                    Text(app.detailOn ? "Back to the short version" : teaser).font(.clSecondary).foregroundStyle(Palette.muted)
                }
                Spacer()
                Image(systemName: "chevron.down").font(.system(size: 17, weight: .semibold)).foregroundStyle(Palette.text2)
                    .rotationEffect(.degrees(app.detailOn ? 180 : 0))
            }
            .padding(.horizontal, 16).padding(.vertical, 12)
            .frame(minHeight: 56)
            .background(RoundedRectangle(cornerRadius: Radius.md, style: .continuous).fill(Palette.panel2))
            .contentShape(RoundedRectangle(cornerRadius: Radius.md, style: .continuous))
        }
        .buttonStyle(StateLayerStyle(shape: RoundedRectangle(cornerRadius: Radius.md, style: .continuous)))
        .accessibilityIdentifier("more-detail")
        .accessibilityValue(app.detailOn ? "Expanded" : "Collapsed")
    }
}

/// Data status as words, not pills (§4.9): estimates muted with a dashed square, examples brown with a hatched square.
struct StatusWord: View {
    typealias Kind = AnswerStatus.Kind
    let kind: Kind
    var text: String?

    var body: some View {
        HStack(spacing: 5) {
            ZStack {
                if kind == .estimate {
                    RoundedRectangle(cornerRadius: 2).strokeBorder(Palette.muted, style: StrokeStyle(lineWidth: 1, dash: [2, 1.5]))
                } else {
                    RoundedRectangle(cornerRadius: 2).fill(Palette.warn.opacity(0.18))
                    Hatch().stroke(Palette.warn, lineWidth: 1).clipShape(RoundedRectangle(cornerRadius: 2))
                    RoundedRectangle(cornerRadius: 2).strokeBorder(Palette.warn, lineWidth: 1)
                }
            }
            .frame(width: 10, height: 10)
            Text(text ?? (kind == .estimate ? "Estimated." : "Example numbers."))
                .font(.clSecondary).italic()
                .foregroundStyle(kind == .estimate ? Palette.muted : Palette.warn)
        }
        .accessibilityElement(children: .combine)
    }
}

struct Hatch: Shape {
    var spacing: CGFloat = 3
    func path(in r: CGRect) -> Path {
        var p = Path()
        var x = r.minX - r.height
        while x < r.maxX {
            p.move(to: CGPoint(x: x, y: r.maxY)); p.addLine(to: CGPoint(x: x + r.height, y: r.minY))
            x += spacing
        }
        return p
    }
}

/// The once-per-panel notice (example numbers, offline).
struct NoticeView: View {
    let text: String
    var body: some View {
        Text(text).font(.clSecondary).foregroundStyle(Palette.onWarnContainer)
            .padding(.horizontal, 16).padding(.vertical, 12)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(RoundedRectangle(cornerRadius: Radius.md, style: .continuous).fill(Palette.warnContainer))
    }
}

/// A small fact chip in the field header: "149 acres", "Rice in 2025", "Colusa County".
struct FactChip: View {
    var dot: Color?
    let text: Text
    var body: some View {
        HStack(spacing: 6) {
            if let dot { Circle().fill(dot).frame(width: 8, height: 8) }
            text.font(.clSecondary).foregroundStyle(Palette.text2).lineLimit(1)
        }
        .padding(.horizontal, 10).frame(height: 28)
        .background(Capsule().fill(Palette.panel2))
    }
}

/// Raised card: the glance card (the only card in a panel).
struct Card<Content: View>: View {
    var padding: CGFloat = 12
    @ViewBuilder let content: Content
    var body: some View {
        VStack(alignment: .leading, spacing: 12) { content }
            .padding(padding)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(RoundedRectangle(cornerRadius: Radius.md, style: .continuous).fill(Palette.raised))
            .overlay(RoundedRectangle(cornerRadius: Radius.md, style: .continuous).strokeBorder(Palette.lineSoft))
            .elevation1()
    }
}

/// A full-width row with a title, a one-line description and a chevron (next steps, events).
struct ChevronRow: View {
    let title: String
    var subtitle: String?
    var leading: String?
    let action: () -> Void
    var body: some View {
        Button(action: action) {
            HStack(spacing: 12) {
                if let leading { Image(systemName: leading).foregroundStyle(Palette.accent).frame(width: 22) }
                VStack(alignment: .leading, spacing: 2) {
                    Text(title).font(.clBodyStrong).foregroundStyle(Palette.text).multilineTextAlignment(.leading)
                    if let subtitle { Text(subtitle).font(.clCite).foregroundStyle(Palette.muted).multilineTextAlignment(.leading) }
                }
                Spacer(minLength: 8)
                Image(systemName: "chevron.right").font(.system(size: 14, weight: .semibold)).foregroundStyle(Palette.muted)
            }
            .padding(.horizontal, 12).padding(.vertical, 10)
            .frame(minHeight: 48)
            .contentShape(RoundedRectangle(cornerRadius: Radius.md, style: .continuous))
        }
        .buttonStyle(StateLayerStyle(shape: RoundedRectangle(cornerRadius: Radius.md, style: .continuous)))
    }
}
