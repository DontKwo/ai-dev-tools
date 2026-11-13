import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';

class FlutterAuditDriver {
  final WidgetTester tester;
  final List<Map<String, dynamic>> interactions = [];
  int seq = 0;

  FlutterAuditDriver(this.tester);

  Future<void> realClick(Key key, String id) async {
    await tester.tap(find.byKey(key));
    await tester.pumpAndSettle();
    seq++;
    interactions.add({
      'control_id': id,
      'input_kind': 'touch',
      'trusted': true,
      'control_state': 'enabled',
      'sequence_number': seq,
    });
  }
}
