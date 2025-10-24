import flet as ft
from flet import Colors
from statrep_db_v3_prod import StatrepDatabase
from manage_handles_v3_prod import HandlesDatabase
from manage_locations_v3_prod import LocationDatabase
from datetime import datetime
from zoneinfo import ZoneInfo
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_central_time():
    """Get current time in US Central timezone (handles DST automatically)"""
    try:
        # Use America/Chicago which automatically handles CST/CDT
        central_tz = ZoneInfo("America/Chicago")
        return datetime.now(central_tz)
    except Exception as e:
        logger.warning(f"Could not use zoneinfo, falling back to UTC-6: {e}")
        # Fallback: simple UTC-6 offset (doesn't handle DST)
        from datetime import timezone, timedelta
        central_tz = timezone(timedelta(hours=-6))
        return datetime.now(central_tz)

class StatrepApp:
    def __init__(self):
        self.db = None
        self.handles_db = None
        self.locations_db = None
        
    def main(self, page: ft.Page):
        page.title = "ReadyCorps STATREP Submission"
        page.theme_mode = "light"
        page.padding = 20
        page.scroll = "auto"
        
        # Status message (for connection errors, etc.)
        connection_status = ft.Text(value="", size=14)
        
        # Initialize Oracle databases with error handling
        logger.info("Initializing database connections...")
        
        self.db = StatrepDatabase()
        success, error = self.db.connect()
        if not success:
            connection_status.value = f"❌ Database Error: {error}"
            connection_status.color = Colors.RED
            page.add(
                ft.Column([
                    ft.Text("ReadyCorps STATREP Submission", size=32, weight="bold"),
                    ft.Divider(height=20),
                    connection_status,
                    ft.Text("\nPlease contact your administrator.", size=14, color=Colors.GREY_700)
                ])
            )
            return
        
        self.handles_db = HandlesDatabase()
        success, error = self.handles_db.connect()
        if not success:
            connection_status.value = f"❌ Handles Database Error: {error}"
            connection_status.color = Colors.RED
            page.add(
                ft.Column([
                    ft.Text("ReadyCorps STATREP Submission", size=32, weight="bold"),
                    ft.Divider(height=20),
                    connection_status,
                    ft.Text("\nPlease contact your administrator.", size=14, color=Colors.GREY_700)
                ])
            )
            return
        
        self.locations_db = LocationDatabase()
        success, error = self.locations_db.connect()
        if not success:
            connection_status.value = f"❌ Locations Database Error: {error}"
            connection_status.color = Colors.RED
            page.add(
                ft.Column([
                    ft.Text("ReadyCorps STATREP Submission", size=32, weight="bold"),
                    ft.Divider(height=20),
                    connection_status,
                    ft.Text("\nPlease contact your administrator.", size=14, color=Colors.GREY_700)
                ])
            )
            return
        
        # Get lists of valid options
        success, valid_handles = self.handles_db.get_all_handles()
        if not success:
            valid_handles = []
        
        success, valid_states = self.locations_db.get_all_states()
        if not success:
            valid_states = []
        
        success, valid_neighborhoods = self.locations_db.get_all_neighborhoods()
        if not success:
            valid_neighborhoods = []
        
        # Store valid options
        self.valid_handles = valid_handles
        self.valid_states = valid_states
        self.valid_neighborhoods = valid_neighborhoods
        
        logger.info(f"Data loaded - Handles: {len(valid_handles)}, States: {len(valid_states)}, Neighborhoods: {len(valid_neighborhoods)}")
        
        # Status message for user feedback
        self.status_message = ft.Text(value="", color=Colors.GREEN, size=16, weight="bold")
        
        # ===== HANDLE FIELD =====
        self.handle_field = ft.TextField(
            label="Your ReadyCore Handle",
            hint_text="Start typing to search handles...",
            width=400,
            autofocus=True,
            on_change=lambda e: self.filter_handles(e, page)
        )
        
        self.handle_suggestions = ft.Column(
            controls=[],
            visible=False,
            scroll="auto",
            height=200,
            width=400
        )
        
        # ===== PIN FIELD =====
        self.pin_field = ft.TextField(
            label="PIN",
            hint_text="Enter your 4-digit PIN",
            password=True,
            can_reveal_password=True,
            width=250,
            max_length=10
        )
        
        # Verify PIN button
        verify_pin_button = ft.ElevatedButton(
            text="Verify PIN",
            on_click=lambda e: self.verify_pin_clicked(page),
            bgcolor=Colors.BLUE_700,
            color=Colors.WHITE,
            height=40
        )
        
        # Change PIN button (always visible alongside Verify)
        def change_pin_button_clicked(e):
            logger.info("Change PIN button clicked!")
            logger.info(f"Event page: {e.page}, Control page: {e.control.page}")
            self.show_voluntary_pin_change(e.control.page)
        
        change_pin_button = ft.ElevatedButton(
            text="Change PIN",
            on_click=change_pin_button_clicked,
            bgcolor=Colors.ORANGE_700,
            color=Colors.WHITE,
            height=40
        )
        
        self.pin_row = ft.Row(
            controls=[self.pin_field, verify_pin_button, change_pin_button],
            spacing=10,
            alignment=ft.MainAxisAlignment.START
        )
        self.verify_pin_button = verify_pin_button  # Store reference
        self.change_pin_button = change_pin_button  # Store reference
        self.pin_verified = False  # Track if PIN has been verified
        
        # ===== DATETIME FIELD =====
        current_dt = get_central_time().strftime("%Y-%m-%d %H:%M")
        self.datetime_field = ft.TextField(
            label="Report as of Date/Time",
            hint_text="YYYY-MM-DD HH:MM",
            value=current_dt,
            width=400,
            helper_text="US Central Time (CST/CDT)"
        )
        
        # ===== STATE FIELD =====
        self.state_field = ft.TextField(
            label="State / Territory",
            hint_text="Start typing to search states...",
            width=400,
            on_change=lambda e: self.filter_states(e, page)
        )
        
        self.state_suggestions = ft.Column(
            controls=[],
            visible=False,
            scroll="auto",
            height=200,
            width=400
        )
        
        # ===== NEIGHBORHOOD FIELD =====
        self.neighborhood_field = ft.TextField(
            label="Neighborhood",
            hint_text="Start typing to search neighborhoods...",
            width=400,
            on_change=lambda e: self.filter_neighborhoods(e, page)
        )
        
        self.neighborhood_suggestions = ft.Column(
            controls=[],
            visible=False,
            scroll="auto",
            height=200,
            width=400
        )
        
        # ===== LOCATION FIELD =====
        self.location_field = ft.TextField(
            label="Your Location",
            hint_text="Grid Square (e.g., FN20xb) or City, State",
            width=400,
            multiline=True,
            min_lines=2,
            max_lines=4,
            helper_text="Grid Square Preferred. Include any additional details to help \nlocate you (e.g., near downtown, 2nd floor, etc.)"
        )
        
        # Radio button groups
        self.conditions_group = ft.RadioGroup(
            content=ft.Column([
                ft.Radio(value="A", label="A - All Stable"),
                ft.Radio(value="B", label="B - Moderate Disruptions"),
                ft.Radio(value="C", label="C - Severe Disruptions"),
            ]),
            value="A"
        )
        
        self.position_group = ft.RadioGroup(
            content=ft.Column([
                ft.Radio(value="H", label="H - Home"),
                ft.Radio(value="M", label="M - Mobile"),
                ft.Radio(value="P", label="P - Portable"),
            ])
        )
        
        self.power_group = ft.RadioGroup(
            content=ft.Column([
                ft.Radio(value="Y", label="Y - Up and Running"),
                ft.Radio(value="I", label="I - Intermittent / Brown-outs"),
                ft.Radio(value="N", label="N - No, Commercial Power is down"),
            ])
        )
        
        self.water_group = ft.RadioGroup(
            content=ft.Column([
                ft.Radio(value="Y", label="Y - Yes"),
                ft.Radio(value="C", label="C - Contaminated"),
                ft.Radio(value="N", label="N - No"),
            ])
        )
        
        self.sanitation_group = ft.RadioGroup(
            content=ft.Column([
                ft.Radio(value="Y", label="Y - Yes"),
                ft.Radio(value="N", label="N - No"),
            ])
        )
        
        self.grid_comms_group = ft.RadioGroup(
            content=ft.Column([
                ft.Radio(value="Y", label="Y - Yes"),
                ft.Radio(value="N", label="N - No"),
            ])
        )
        
        self.transport_group = ft.RadioGroup(
            content=ft.Column([
                ft.Radio(value="Y", label="Y - Yes"),
                ft.Radio(value="N", label="N - No"),
            ])
        )
        
        self.comments_field = ft.TextField(
            label="Comments",
            multiline=True,
            min_lines=3,
            max_lines=5,
            width=400
        )
        
        # Optional fields container (shown when conditions != 'A')
        self.optional_fields = ft.Column(
            controls=[
                ft.Divider(height=20),
                ft.Text("Additional Information (Optional for 'All Stable' reports)", 
                       size=16, weight="bold"),
                ft.Text("Your Position:", weight="bold"),
                self.position_group,
                ft.Text("Status of Commercial Power:", weight="bold"),
                self.power_group,
                ft.Text("Water Status:", weight="bold"),
                self.water_group,
                ft.Text("Sanitation Status:", weight="bold"),
                self.sanitation_group,
                ft.Text("Grid Communications:", weight="bold"),
                self.grid_comms_group,
                ft.Text("Transportation Status:", weight="bold"),
                self.transport_group,
                ft.Divider(height=10),
                self.comments_field,
            ],
            visible=False
        )
        
        # Add listener to conditions radio group to show/hide optional fields
        def conditions_changed(e):
            if self.conditions_group.value != "A":
                self.optional_fields.visible = True
            else:
                self.optional_fields.visible = False
            page.update()
        
        self.conditions_group.on_change = conditions_changed
        
        # Verify PIN handler (acts as "login")
        def verify_pin_clicked(page):
            # Validate inputs
            if not self.handle_field.value:
                self.status_message.value = "✗ Please select a handle first"
                self.status_message.color = Colors.RED
                page.update()
                return
            
            if not self.pin_field.value:
                self.status_message.value = "✗ Please enter your PIN"
                self.status_message.color = Colors.RED
                page.update()
                return
            
            # Verify PIN
            if not self.handles_db.verify_pin(self.handle_field.value, self.pin_field.value):
                self.status_message.value = "✗ Invalid handle or PIN"
                self.status_message.color = Colors.RED
                self.pin_verified = False
                page.update()
                return
            
            # PIN is valid!
            self.pin_verified = True
            logger.info("PIN verified successfully")
            
            # Check if PIN needs to be changed (starts with 'z')
            if self.handles_db.pin_needs_change(self.handle_field.value, self.pin_field.value):
                self.show_pin_change_dialog(self.handle_field.value, page)
                return  # Don't continue until PIN is changed
            
            # Look up the last STATREP for this handle (pre-fill convenience)
            success, last_statrep = self.db.get_last_statrep_for_handle(self.handle_field.value)
            
            if success and last_statrep:
                # Pre-populate state, neighborhood, and location from last report
                self.state_field.value = last_statrep[3]  # state
                self.neighborhood_field.value = last_statrep[4]  # neighborhood
                self.location_field.value = last_statrep[5]  # location
                
                # Show success message with pre-fill info
                self.status_message.value = f"✓ Verified! Pre-filled from your last report ({last_statrep[2]})"
                self.status_message.color = Colors.GREEN
            else:
                # First time for this handle
                self.status_message.value = f"✓ Verified! Welcome, {self.handle_field.value}"
                self.status_message.color = Colors.GREEN
            
            page.update()
        
        self.verify_pin_clicked = verify_pin_clicked
        
        # Submit button handler
        def submit_clicked(e):
            # Validate required fields
            if not self.handle_field.value:
                self.status_message.value = "✗ Please select your handle"
                self.status_message.color = Colors.RED
                page.update()
                return
            
            if not self.pin_field.value:
                self.status_message.value = "✗ Please enter your PIN"
                self.status_message.color = Colors.RED
                page.update()
                return
            
            # Verify PIN inline (unless already verified)
            if not self.pin_verified:
                if not self.handles_db.verify_pin(self.handle_field.value, self.pin_field.value):
                    self.status_message.value = "✗ Invalid handle or PIN"
                    self.status_message.color = Colors.RED
                    page.update()
                    return
                
                # Check if PIN needs to be changed (starts with 'z')
                if self.handles_db.pin_needs_change(self.handle_field.value, self.pin_field.value):
                    # Show forced change dialog - mark as verified after they change
                    self.show_pin_change_dialog(self.handle_field.value, page)
                    return  # Don't submit yet, wait for PIN change
            
            # PIN is valid, continue with submission
            if not self.datetime_field.value:
                self.status_message.value = "✗ Please enter date/time"
                self.status_message.color = Colors.RED
                page.update()
                return
            
            if not self.state_field.value:
                self.status_message.value = "✗ Please enter state"
                self.status_message.color = Colors.RED
                page.update()
                return
            
            if not self.neighborhood_field.value:
                self.status_message.value = "✗ Please enter neighborhood"
                self.status_message.color = Colors.RED
                page.update()
                return
            
            if not self.location_field.value:
                self.status_message.value = "✗ Please enter location"
                self.status_message.color = Colors.RED
                page.update()
                return
            
            # Insert the STATREP
            success, result = self.db.insert_statrep(
                amcon_handle=self.handle_field.value,
                datetime_group=self.datetime_field.value,
                state=self.state_field.value,
                neighborhood=self.neighborhood_field.value,
                location=self.location_field.value,
                conditions=self.conditions_group.value,
                position=self.position_group.value if self.conditions_group.value != "A" else None,
                commercial_power=self.power_group.value if self.conditions_group.value != "A" else None,
                water=self.water_group.value if self.conditions_group.value != "A" else None,
                sanitation=self.sanitation_group.value if self.conditions_group.value != "A" else None,
                grid_comms=self.grid_comms_group.value if self.conditions_group.value != "A" else None,
                transportation=self.transport_group.value if self.conditions_group.value != "A" else None,
                comments=self.comments_field.value if self.comments_field.value else None
            )
            
            if success:
                # Update last_used timestamp for the handle
                self.handles_db.update_last_used(self.handle_field.value)
                
                # Save handle for re-population after clear
                submitted_handle = self.handle_field.value
                
                # Mark as verified (for next time)
                self.pin_verified = True
                
                self.status_message.value = f"✓ STATREP submitted successfully! (ID: {result})"
                self.status_message.color = Colors.GREEN
                
                # Clear form except handle (for quick re-submissions)
                clear_form(None)
                
                # Re-populate handle and keep verified state for convenience
                self.handle_field.value = submitted_handle
                self.pin_verified = True
            else:
                self.status_message.value = f"✗ Error: {result}"
                self.status_message.color = Colors.RED
            
            page.update()
        
        def clear_form(e):
            self.handle_field.value = ""
            self.pin_field.value = ""
            self.datetime_field.value = get_central_time().strftime("%Y-%m-%d %H:%M")
            self.state_field.value = ""
            self.neighborhood_field.value = ""
            self.location_field.value = ""
            self.conditions_group.value = "A"
            self.position_group.value = None
            self.power_group.value = None
            self.water_group.value = None
            self.sanitation_group.value = None
            self.grid_comms_group.value = None
            self.transport_group.value = None
            self.comments_field.value = ""
            self.optional_fields.visible = False
            self.handle_suggestions.visible = False
            self.handle_suggestions.controls.clear()
            self.state_suggestions.visible = False
            self.state_suggestions.controls.clear()
            self.neighborhood_suggestions.visible = False
            self.neighborhood_suggestions.controls.clear()
            # Reset PIN verification state
            self.pin_verified = False
            if e:  # Only clear status message if user clicked clear button
                self.status_message.value = ""
            page.update()
        
        def show_statreps_clicked(e):
            """Show recent STATREPs for the same state/neighborhood"""
            
            # Validate that state and neighborhood are filled
            if not self.state_field.value:
                self.status_message.value = "✗ Please enter a state first"
                self.status_message.color = Colors.RED
                page.update()
                return
            
            if not self.neighborhood_field.value:
                self.status_message.value = "✗ Please enter a neighborhood first"
                self.status_message.color = Colors.RED
                page.update()
                return
            
            state = self.state_field.value
            neighborhood = self.neighborhood_field.value
            
            logger.info(f"Fetching STATREPs for {state}/{neighborhood}")
            
            # Query the database
            success, results = self.db.get_latest_statreps_by_location(state, neighborhood)
            
            if not success:
                self.status_message.value = f"✗ Error fetching STATREPs: {results}"
                self.status_message.color = Colors.RED
                page.update()
                return
            
            if not results or len(results) == 0:
                self.status_message.value = f"ℹ No STATREPs found for {state}/{neighborhood}"
                self.status_message.color = Colors.BLUE
                page.update()
                return
            
            # Build the table
            show_statreps_dialog(page, results, state, neighborhood)
        
        def show_statreps_dialog(page, results, state, neighborhood):
            """Display STATREPs in a scrollable dialog with table"""
            
            # Map condition codes to descriptions
            condition_map = {
                "A": "All Stable",
                "B": "Moderate Disruptions",
                "C": "Severe Disruptions"
            }
            
            # Create table rows
            table_rows = []
            
            for row in results:
                # row structure: id, amcon_handle, datetime_group, state, neighborhood, location, 
                #                conditions, position, commercial_power, water, sanitation, 
                #                grid_comms, transportation, comments
                handle = row[1]
                datetime_str = str(row[2])
                conditions = row[6]
                condition_desc = condition_map.get(conditions, conditions)
                
                if conditions == "A":
                    # All Stable - just show that
                    table_rows.append(
                        ft.DataRow(
                            cells=[
                                ft.DataCell(ft.Text(handle, size=12)),
                                ft.DataCell(ft.Text(datetime_str, size=12)),
                                ft.DataCell(ft.Text(condition_desc, size=12, weight="bold", color=Colors.GREEN)),
                                ft.DataCell(ft.Text("")),
                                ft.DataCell(ft.Text("")),
                                ft.DataCell(ft.Text("")),
                                ft.DataCell(ft.Text("")),
                                ft.DataCell(ft.Text("")),
                                ft.DataCell(ft.Text("")),
                                ft.DataCell(ft.Text("")),
                            ]
                        )
                    )
                else:
                    # Moderate or Severe - show all fields
                    position = row[7] or ""
                    power = row[8] or ""
                    water = row[9] or ""
                    sanitation = row[10] or ""
                    grid_comms = row[11] or ""
                    transportation = row[12] or ""
                    comments = row[13] or ""
                    
                    color = Colors.ORANGE if conditions == "B" else Colors.RED
                    
                    table_rows.append(
                        ft.DataRow(
                            cells=[
                                ft.DataCell(ft.Text(handle, size=12)),
                                ft.DataCell(ft.Text(datetime_str, size=12)),
                                ft.DataCell(ft.Text(condition_desc, size=12, weight="bold", color=color)),
                                ft.DataCell(ft.Text(position, size=11)),
                                ft.DataCell(ft.Text(power, size=11)),
                                ft.DataCell(ft.Text(water, size=11)),
                                ft.DataCell(ft.Text(sanitation, size=11)),
                                ft.DataCell(ft.Text(grid_comms, size=11)),
                                ft.DataCell(ft.Text(transportation, size=11)),
                                ft.DataCell(ft.Text(comments[:30] + "..." if len(comments) > 30 else comments, size=11)),
                            ]
                        )
                    )
            
            # Create the data table
            data_table = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("Handle", weight="bold", size=13)),
                    ft.DataColumn(ft.Text("Date/Time", weight="bold", size=13)),
                    ft.DataColumn(ft.Text("Status", weight="bold", size=13)),
                    ft.DataColumn(ft.Text("Position", weight="bold", size=13)),
                    ft.DataColumn(ft.Text("Power", weight="bold", size=13)),
                    ft.DataColumn(ft.Text("Water", weight="bold", size=13)),
                    ft.DataColumn(ft.Text("Sanitation", weight="bold", size=13)),
                    ft.DataColumn(ft.Text("Grid/Comms", weight="bold", size=13)),
                    ft.DataColumn(ft.Text("Transport", weight="bold", size=13)),
                    ft.DataColumn(ft.Text("Comments", weight="bold", size=13)),
                ],
                rows=table_rows,
                border=ft.border.all(1, Colors.GREY_400),
                border_radius=10,
                horizontal_lines=ft.border.BorderSide(1, Colors.GREY_300),
                heading_row_color=Colors.BLUE_GREY_100,
            )
            
            def close_dialog(e):
                page.close(statreps_dialog)
            
            # Create scrollable container for the table
            statreps_dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text(f"Recent STATREPs - {state} / {neighborhood}", size=20, weight="bold"),
                content=ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text(
                                f"Showing {len(results)} most recent report(s)",
                                size=14,
                                color=Colors.GREY_700
                            ),
                            ft.Divider(height=10),
                            data_table,
                        ],
                        scroll="auto",
                        spacing=10,
                    ),
                    width=1200,
                    height=500,
                    padding=10,
                ),
                actions=[
                    ft.ElevatedButton(
                        text="Close",
                        on_click=close_dialog,
                        bgcolor=Colors.BLUE_700,
                        color=Colors.WHITE
                    )
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            
            page.open(statreps_dialog)
        
        submit_button = ft.ElevatedButton(
            text="Submit STATREP",
            on_click=submit_clicked,
            width=200,
            bgcolor=Colors.GREEN_700,
            color=Colors.WHITE,
            height=50
        )
        
        show_statreps_button = ft.ElevatedButton(
            text="Show STATREPs",
            on_click=show_statreps_clicked,
            width=200,
            bgcolor=Colors.BLUE_700,
            color=Colors.WHITE,
            height=50
        )
        
        # Build the page
        page.add(
            ft.Column(
                controls=[
                    ft.Text("ReadyCorps STATREP Submission", size=32, weight="bold"),
                    ft.Text("Use this form to submit your Status Report", size=16),
                    ft.Divider(height=20),
                    ft.Container(
                        content=ft.Text(
                            "📝 Fill out the form and click Submit.\n"
                            "🔐 Verify PIN to auto-fill from your last report, or Change PIN if needed.",
                            size=13,
                            color=Colors.GREY_700,
                            italic=True
                        ),
                        padding=ft.padding.only(left=10, bottom=10)
                    ),
                    self.status_message,
                    ft.Divider(height=20),
                    
                    # Required fields
                    self.handle_field,
                    self.handle_suggestions,
                    self.pin_row,
                    self.datetime_field,
                    self.state_field,
                    self.state_suggestions,
                    self.neighborhood_field,
                    self.neighborhood_suggestions,
                    self.location_field,
                    
                    ft.Text("Current Conditions:", size=16, weight="bold"),
                    self.conditions_group,
                    
                    # Optional fields (hidden by default)
                    self.optional_fields,
                    
                    # Buttons
                    ft.Divider(height=20),
                    ft.Row(
                        controls=[submit_button, show_statreps_button],
                        spacing=20
                    ),
                ],
                spacing=10,
                scroll="auto"
            )
        )
        
        # Cleanup on close
        def on_close(e):
            logger.info("Application closing - cleaning up database connections")
            if self.db:
                self.db.close()
            if self.handles_db:
                self.handles_db.close()
            if self.locations_db:
                self.locations_db.close()
        
        page.on_close = on_close
    
    def show_pin_change_dialog(self, handle, page):
        """Show modal dialog to force PIN change for temporary PINs"""
        
        # Dialog fields
        new_pin_field = ft.TextField(
            label="New PIN",
            hint_text="Enter new PIN (4+ characters)",
            password=True,
            can_reveal_password=True,
            width=300,
            autofocus=True
        )
        
        confirm_pin_field = ft.TextField(
            label="Confirm New PIN",
            hint_text="Re-enter new PIN",
            password=True,
            can_reveal_password=True,
            width=300
        )
        
        dialog_status = ft.Text(value="", color=Colors.RED, size=12)
        
        def change_pin_clicked(e):
            # Validate inputs
            new_pin = new_pin_field.value
            confirm_pin = confirm_pin_field.value
            
            if not new_pin or not confirm_pin:
                dialog_status.value = "Please enter PIN in both fields"
                page.update()
                return
            
            if len(new_pin) < 4:
                dialog_status.value = "PIN must be at least 4 characters"
                page.update()
                return
            
            if new_pin != confirm_pin:
                dialog_status.value = "PINs do not match"
                page.update()
                return
            
            if new_pin.lower().startswith('z'):
                dialog_status.value = "New PIN cannot start with 'z' (reserved for temporary PINs)"
                page.update()
                return
            
            # Change the PIN
            success, error = self.handles_db.change_pin(handle, new_pin)
            
            if success:
                # Close dialog using correct Flet API
                page.close(pin_change_dialog)
                
                # Update the PIN field with new PIN so verification passes
                self.pin_field.value = new_pin
                
                # Mark as verified (they just changed from temp PIN)
                self.pin_verified = True
                
                # Pre-fill their last STATREP data if any
                success_fetch, last_statrep = self.db.get_last_statrep_for_handle(handle)
                if success_fetch and last_statrep:
                    self.state_field.value = last_statrep[3]
                    self.neighborhood_field.value = last_statrep[4]
                    self.location_field.value = last_statrep[5]
                
                # Show success message
                self.status_message.value = f"✓ PIN changed successfully! You can now submit reports."
                self.status_message.color = Colors.GREEN
                
                page.update()
            else:
                dialog_status.value = f"Error: {error}"
                page.update()
        
        # Create the dialog
        pin_change_dialog = ft.AlertDialog(
            modal=True,  # User must change PIN before continuing
            title=ft.Text("Change Your PIN", size=20, weight="bold"),
            content=ft.Column(
                controls=[
                    ft.Text(
                        f"Welcome, {handle}!",
                        size=16,
                        weight="bold"
                    ),
                    ft.Text(
                        "Your PIN starts with 'z' which is temporary.",
                        size=14
                    ),
                    ft.Text(
                        "Please change it to your own PIN to continue.",
                        size=14,
                        color=Colors.BLUE_700
                    ),
                    ft.Divider(height=20),
                    new_pin_field,
                    confirm_pin_field,
                    dialog_status,
                ],
                tight=True,
                spacing=10,
                width=400
            ),
            actions=[
                ft.ElevatedButton(
                    text="Change PIN",
                    on_click=change_pin_clicked,
                    bgcolor=Colors.BLUE_700,
                    color=Colors.WHITE
                )
            ],
            actions_alignment=ft.MainAxisAlignment.CENTER,
        )
        
        page.open(pin_change_dialog)
    
    def show_voluntary_pin_change(self, page):
        """Show dialog for voluntary PIN change (user-initiated)"""
        
        logger.info(f"show_voluntary_pin_change called, page object: {page}")
        logger.info(f"Page type: {type(page)}")
        
        if not self.handle_field.value:
            logger.warning("No handle selected")
            self.status_message.value = "Please select a handle first"
            self.status_message.color = Colors.RED
            page.update()
            return
        
        handle = self.handle_field.value
        logger.info(f"Showing voluntary PIN change dialog for handle: {handle}")
        
        # Dialog fields
        old_pin_field = ft.TextField(
            label="Current PIN",
            hint_text="Enter your current PIN",
            password=True,
            can_reveal_password=True,
            width=300,
            autofocus=True
        )
        
        new_pin_field = ft.TextField(
            label="New PIN",
            hint_text="Enter new PIN (4+ characters)",
            password=True,
            can_reveal_password=True,
            width=300
        )
        
        confirm_pin_field = ft.TextField(
            label="Confirm New PIN",
            hint_text="Re-enter new PIN",
            password=True,
            can_reveal_password=True,
            width=300
        )
        
        dialog_status = ft.Text(value="", color=Colors.RED, size=12)
        
        def change_pin_clicked(e):
            # Verify old PIN first
            if not self.handles_db.verify_pin(handle, old_pin_field.value):
                dialog_status.value = "Current PIN is incorrect"
                page.update()
                return
            
            # Validate new PIN inputs
            new_pin = new_pin_field.value
            confirm_pin = confirm_pin_field.value
            
            if not new_pin or not confirm_pin:
                dialog_status.value = "Please enter PIN in both fields"
                page.update()
                return
            
            if len(new_pin) < 4:
                dialog_status.value = "PIN must be at least 4 characters"
                page.update()
                return
            
            if new_pin != confirm_pin:
                dialog_status.value = "New PINs do not match"
                page.update()
                return
            
            if new_pin.lower().startswith('z'):
                dialog_status.value = "PIN cannot start with 'z' (reserved for temporary PINs)"
                page.update()
                return
            
            if new_pin == old_pin_field.value:
                dialog_status.value = "New PIN must be different from current PIN"
                page.update()
                return
            
            # Change the PIN
            success, error = self.handles_db.change_pin(handle, new_pin)
            
            if success:
                # Close dialog using correct Flet API
                page.close(voluntary_pin_dialog)
                
                # Update the PIN field with new PIN
                self.pin_field.value = new_pin
                
                # Show success message
                self.status_message.value = f"✓ PIN changed successfully!"
                self.status_message.color = Colors.GREEN
                
                page.update()
            else:
                dialog_status.value = f"Error: {error}"
                page.update()
        
        def cancel_clicked(e):
            page.close(voluntary_pin_dialog)
        
        # Create the dialog
        voluntary_pin_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Change Your PIN", size=20, weight="bold"),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(
                            f"Changing PIN for: {handle}",
                            size=14,
                            weight="bold"
                        ),
                        ft.Divider(height=20),
                        old_pin_field,
                        new_pin_field,
                        confirm_pin_field,
                        dialog_status,
                    ],
                    tight=True,
                    spacing=10,
                ),
                width=400,
                padding=20
            ),
            actions=[
                ft.TextButton(
                    text="Cancel",
                    on_click=cancel_clicked
                ),
                ft.ElevatedButton(
                    text="Change PIN",
                    on_click=change_pin_clicked,
                    bgcolor=Colors.BLUE_700,
                    color=Colors.WHITE
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        logger.info(f"Dialog object created: {voluntary_pin_dialog}")
        logger.info(f"About to open dialog for handle: {handle}")
        
        # Use the correct Flet API to open dialog
        page.open(voluntary_pin_dialog)
        
        logger.info("Dialog opened with page.open()")
    
    def filter_handles(self, e, page):
        """Filter handles based on user input"""
        search_text = e.control.value.lower()
        
        if not search_text:
            self.handle_suggestions.visible = False
            self.handle_suggestions.controls.clear()
        else:
            filtered = [h for h in self.valid_handles if search_text in h.lower()]
            self.handle_suggestions.controls.clear()
            
            if filtered:
                for handle in filtered[:10]:
                    btn = ft.TextButton(
                        text=handle,
                        on_click=lambda e, h=handle: self.select_handle(h, page),
                        style=ft.ButtonStyle(padding=10)
                    )
                    self.handle_suggestions.controls.append(btn)
                self.handle_suggestions.visible = True
            else:
                self.handle_suggestions.controls.append(
                    ft.Text("No matching handles found", color=Colors.GREY_700, size=12)
                )
                self.handle_suggestions.visible = True
        
        page.update()
    
    def select_handle(self, handle, page):
        """Select a handle from suggestions"""
        self.handle_field.value = handle
        self.handle_suggestions.visible = False
        self.handle_suggestions.controls.clear()
        
        # Focus on PIN field for next step
        self.pin_field.focus()
        
        # Show helpful message
        self.status_message.value = f"Selected: {handle}. Now enter your PIN and click Verify."
        self.status_message.color = Colors.BLUE
        
        page.update()
    
    def filter_states(self, e, page):
        """Filter states based on user input"""
        search_text = e.control.value.lower()
        
        if not search_text:
            self.state_suggestions.visible = False
            self.state_suggestions.controls.clear()
        else:
            filtered = [s for s in self.valid_states if search_text in s.lower()]
            self.state_suggestions.controls.clear()
            
            if filtered:
                for state in filtered[:10]:
                    btn = ft.TextButton(
                        text=state,
                        on_click=lambda e, s=state: self.select_state(s, page),
                        style=ft.ButtonStyle(padding=10)
                    )
                    self.state_suggestions.controls.append(btn)
                self.state_suggestions.visible = True
            else:
                self.state_suggestions.controls.append(
                    ft.Text("No matching states found", color=Colors.GREY_700, size=12)
                )
                self.state_suggestions.visible = True
        
        page.update()
    
    def select_state(self, state, page):
        """Select a state from suggestions"""
        self.state_field.value = state
        self.state_suggestions.visible = False
        self.state_suggestions.controls.clear()
        self.neighborhood_field.focus()
        page.update()
    
    def filter_neighborhoods(self, e, page):
        """Filter neighborhoods based on user input"""
        search_text = e.control.value.lower()
        
        if not search_text:
            self.neighborhood_suggestions.visible = False
            self.neighborhood_suggestions.controls.clear()
        else:
            filtered = [n for n in self.valid_neighborhoods if search_text in n.lower()]
            self.neighborhood_suggestions.controls.clear()
            
            if filtered:
                for neighborhood in filtered[:10]:
                    btn = ft.TextButton(
                        text=neighborhood,
                        on_click=lambda e, n=neighborhood: self.select_neighborhood(n, page),
                        style=ft.ButtonStyle(padding=10)
                    )
                    self.neighborhood_suggestions.controls.append(btn)
                self.neighborhood_suggestions.visible = True
            else:
                self.neighborhood_suggestions.controls.append(
                    ft.Text("No matching neighborhoods found", color=Colors.GREY_700, size=12)
                )
                self.neighborhood_suggestions.visible = True
        
        page.update()
    
    def select_neighborhood(self, neighborhood, page):
        """Select a neighborhood from suggestions"""
        self.neighborhood_field.value = neighborhood
        self.neighborhood_suggestions.visible = False
        self.neighborhood_suggestions.controls.clear()
        self.location_field.focus()
        page.update()

if __name__ == "__main__":
    app = StatrepApp()
    ft.app(target=app.main)
