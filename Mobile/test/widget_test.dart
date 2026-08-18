import 'package:flutter_test/flutter_test.dart';
import 'package:chronos/main.dart';

void main() {
  testWidgets('App smoke test renders onboarding screen by default', (WidgetTester tester) async {
    await tester.pumpWidget(const ChronosApp());
    expect(find.text('Inisiasi Pola Hidup'), findsOneWidget);
  });
}
