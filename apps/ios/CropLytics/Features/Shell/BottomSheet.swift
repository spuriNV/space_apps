import SwiftUI

/// Non-modal bottom sheet over the live map (redesign §5.2): snap points peek (128pt), half (52%) and full.
/// It moves by transform only, follows the finger, and on release snaps to the nearest point or, after a fling,
/// to the next one in that direction, with a spring (instant with Reduce Motion). Tap the grabber to cycle.
/// Content scrolls only at full; below that a drag anywhere on the sheet moves it.
struct BottomSheet<Content: View>: View {
    @Binding var detent: SheetDetent
    let maxHeight: CGFloat
    let screenHeight: CGFloat
    @ViewBuilder let content: Content
    @GestureState(resetTransaction: Transaction(animation: .spring(response: 0.36, dampingFraction: 0.86))) private var dragY: CGFloat = 0
    @Environment(\.accessibilityReduceMotion) private var reduce

    private func visible(_ d: SheetDetent) -> CGFloat { SheetGeometry.visibleHeight(d, screen: screenHeight, max: maxHeight) }

    var body: some View {
        let base = maxHeight - visible(detent)
        let maxOffset = maxHeight - visible(.peek)
        var off = base + dragY
        if off < 0 { off = -pow(-off, 0.7) } else if off > maxOffset { off = maxOffset + pow(off - maxOffset, 0.7) }
        let shape = UnevenRoundedRectangle(topLeadingRadius: Radius.xl, topTrailingRadius: Radius.xl, style: .continuous)
        return VStack(spacing: 0) {
            grabber
            content
                .frame(maxHeight: .infinity, alignment: .top)
        }
        .frame(height: maxHeight, alignment: .top)
        .background(shape.fill(Palette.paper))
        .clipShape(shape)
        .elevationSheet()
        .offset(y: off)
        .gesture(drag, including: detent == .full ? .subviews : .all)
        .animation(Motion.sheet(reduce), value: detent)
        .accessibilityIdentifier("field-sheet")
    }

    private var grabber: some View {
        Button {
            withAnimation(Motion.sheet(reduce)) { detent = detent == .peek ? .half : detent == .half ? .full : .peek }
        } label: {
            Capsule().fill(Palette.outline.opacity(0.6)).frame(width: 36, height: 4)
                .frame(maxWidth: .infinity).frame(height: 24)
                .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .highPriorityGesture(drag)
        .accessibilityLabel("Resize the field panel")
        .accessibilityValue(detent == .peek ? "Small" : detent == .half ? "Half" : "Full")
        .accessibilityAdjustableAction { dir in
            withAnimation(Motion.sheet(reduce)) {
                switch dir {
                case .increment: detent = SheetDetent(rawValue: min(2, detent.rawValue + 1)) ?? detent
                case .decrement: detent = SheetDetent(rawValue: max(0, detent.rawValue - 1)) ?? detent
                @unknown default: break
                }
            }
        }
        .accessibilityIdentifier("sheet-grabber")
    }

    private var drag: some Gesture {
        DragGesture(minimumDistance: 6, coordinateSpace: .global)
            .updating($dragY) { v, state, _ in state = v.translation.height }
            .onEnded { v in
                let current = visible(detent) - v.translation.height
                let predicted = visible(detent) - v.predictedEndTranslation.height
                let fling = abs(v.velocity.height) > 500
                let order = SheetDetent.allCases
                var target: SheetDetent
                if fling {
                    // the next snap point in the direction of the fling
                    target = v.velocity.height < 0
                        ? order.first { visible($0) > current + 1 } ?? .full
                        : order.reversed().first { visible($0) < current - 1 } ?? .peek
                } else {
                    target = order.min { abs(visible($0) - predicted) < abs(visible($1) - predicted) } ?? detent
                }
                withAnimation(Motion.sheet(reduce)) { detent = target }
            }
    }
}
