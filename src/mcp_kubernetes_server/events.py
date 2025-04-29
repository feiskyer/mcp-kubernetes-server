# -*- coding: utf-8 -*-
# pylint: disable=broad-exception-caught
import json
from kubernetes import client
from .get import DateTimeEncoder


async def k8s_events(
    namespace=None,
    all_namespaces=False,
    field_selector=None,
    resource_type=None,
    resource_name=None,
    sort_by=None,
    watch=False,
):
    """
    List events in the cluster.

    :param namespace: The namespace to get events from. If not specified, uses the default namespace.
    :param all_namespaces: Whether to get events from all namespaces.
    :param field_selector: Field selector to filter events (e.g., "involvedObject.kind=Pod").
    :param resource_type: The type of resource to get events for (e.g., pods, deployments).
    :param resource_name: The name of the resource to get events for.
    :param sort_by: Field to sort by (e.g., "lastTimestamp").
    :param watch: Whether to watch for new events.
    :return: The events.
    """
    try:
        # Set default namespace if not provided and not all namespaces
        if not namespace and not all_namespaces:
            namespace = "default"

        # Get the events using the Kubernetes Python SDK
        try:
            # Get the API client
            core_v1 = client.CoreV1Api()

            # Build the field selector
            api_field_selector = field_selector
            if resource_type and resource_name:
                resource_selector = f"involvedObject.kind={resource_type.capitalize()},involvedObject.name={resource_name}"
                if api_field_selector:
                    api_field_selector = f"{api_field_selector},{resource_selector}"
                else:
                    api_field_selector = resource_selector

            # If watch is True, we need to stream the events
            if watch:
                # Get initial events
                if all_namespaces:
                    events_list = core_v1.list_event_for_all_namespaces(
                        field_selector=api_field_selector
                    )
                else:
                    events_list = core_v1.list_namespaced_event(
                        namespace, field_selector=api_field_selector
                    )

                # Format the initial events
                events_output = ""
                for event in events_list.items:
                    event_line = f"{event.metadata.creation_timestamp} {event.type} {event.reason} {event.involved_object.kind}/{event.involved_object.name}: {event.message}\n"
                    events_output += event_line

                # Get the resource version for watching
                resource_version = events_list.metadata.resource_version

                # Watch for new events
                try:
                    w = watch.Watch()

                    # Start watching
                    if all_namespaces:
                        stream = w.stream(
                            core_v1.list_event_for_all_namespaces,
                            field_selector=api_field_selector,
                            resource_version=resource_version,
                            timeout_seconds=10,  # Limit watch to 10 seconds
                        )
                    else:
                        stream = w.stream(
                            core_v1.list_namespaced_event,
                            namespace,
                            field_selector=api_field_selector,
                            resource_version=resource_version,
                            timeout_seconds=10,  # Limit watch to 10 seconds
                        )

                    # Process events from the stream
                    for event in stream:
                        event_obj = event["object"]
                        event_type = event["type"]  # ADDED, MODIFIED, DELETED

                        # Format the event
                        event_line = f"{event_obj.metadata.creation_timestamp} {event_obj.type} {event_obj.reason} {event_obj.involved_object.kind}/{event_obj.involved_object.name}: {event_obj.message} ({event_type})\n"
                        events_output += event_line

                        # Check if we should stop watching
                        if len(events_output) > 1024 * 1024:  # 1MB limit
                            events_output += "\n... event output truncated ...\n"
                            w.stop()
                            break

                except Exception as watch_error:
                    # Watch may timeout or encounter other errors
                    events_output += f"\n... watch ended: {str(watch_error)} ...\n"

                return events_output
            else:
                # Get the events without watching
                if all_namespaces:
                    events = core_v1.list_event_for_all_namespaces(
                        field_selector=api_field_selector
                    )
                else:
                    events = core_v1.list_namespaced_event(
                        namespace, field_selector=api_field_selector
                    )

                # Format the events
                formatted_events = []
                for event in events.items:
                    formatted_event = {
                        "type": event.type,
                        "reason": event.reason,
                        "object": f"{event.involved_object.kind}/{event.involved_object.name}",
                        "message": event.message,
                        "count": event.count,
                        "first_timestamp": event.first_timestamp,
                        "last_timestamp": event.last_timestamp,
                        "source": event.source.component if event.source else None,
                    }

                    if all_namespaces:
                        formatted_event["namespace"] = event.metadata.namespace

                    formatted_events.append(formatted_event)

                # Sort the events if requested
                if sort_by:
                    sort_key = sort_by.lower()
                    if sort_key == "lasttimestamp":
                        formatted_events.sort(
                            key=lambda x: (
                                x["last_timestamp"] if x["last_timestamp"] else ""
                            ),
                            reverse=True,
                        )
                    elif sort_key == "firsttimestamp":
                        formatted_events.sort(
                            key=lambda x: (
                                x["first_timestamp"] if x["first_timestamp"] else ""
                            ),
                            reverse=True,
                        )
                    elif sort_key == "count":
                        formatted_events.sort(
                            key=lambda x: x["count"] if x["count"] else 0, reverse=True
                        )
                    elif sort_key == "type":
                        formatted_events.sort(
                            key=lambda x: x["type"] if x["type"] else ""
                        )
                    elif sort_key == "reason":
                        formatted_events.sort(
                            key=lambda x: x["reason"] if x["reason"] else ""
                        )
                    elif sort_key == "object":
                        formatted_events.sort(
                            key=lambda x: x["object"] if x["object"] else ""
                        )
                    elif sort_key == "source":
                        formatted_events.sort(
                            key=lambda x: x["source"] if x["source"] else ""
                        )

                return json.dumps(formatted_events, indent=2, cls=DateTimeEncoder)

        except Exception as e:
            return f"Error: {str(e)}"
    except Exception as exc:
        return "Error:\n" + str(exc)
