using System.Collections.Generic;

namespace Audit.Ui
{
    public class DotNetAuditDriver
    {
        private readonly List<Dictionary<string, object>> _interactions = new();
        private int _seq = 0;

        public void RecordClick(string controlId)
        {
            _seq++;
            _interactions.Add(new Dictionary<string, object>
            {
                { "control_id", controlId },
                { "input_kind", "mouse" },
                { "trusted", true },
                { "control_state", "enabled" },
                { "sequence_number", _seq }
            });
        }
    }
}
