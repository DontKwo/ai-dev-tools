package com.audit.ui

import androidx.test.espresso.Espresso.onView
import androidx.test.espresso.action.ViewActions.click
import androidx.test.espresso.matcher.ViewMatchers.withId

class AndroidAuditDriver {
    private val interactions = mutableListOf<Map<String, Any>>()
    private var seq = 0

    fun realClick(resId: Int, idString: String) {
        onView(withId(resId)).perform(click())
        seq += 1
        interactions.add(mapOf(
            "control_id" to idString,
            "input_kind" to "touch",
            "trusted" to true,
            "control_state" to "enabled",
            "sequence_number" to seq
        ))
    }
}
