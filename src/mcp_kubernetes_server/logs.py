# -*- coding: utf-8 -*-
# pylint: disable=broad-exception-caught
import datetime
import re

from kubernetes import client


async def k8s_logs(
    pod_name,
    container=None,
    namespace=None,
    tail=None,
    previous=False,
    since=None,
    timestamps=False,
    follow=False,
):
    """
    Print the logs for a container in a pod.

    :param pod_name: The name of the pod.
    :param container: The name of the container in the pod. If not specified, uses the first container.
    :param namespace: The namespace of the pod. If not specified, uses the default namespace.
    :param tail: The number of lines from the end of the logs to show. If not specified, shows all lines.
    :param previous: Whether to show the logs for the previous instance of the container.
    :param since: Only return logs newer than a relative duration like 5s, 2m, or 3h, or an absolute timestamp.
    :param timestamps: Whether to include timestamps on each line.
    :param follow: Whether to follow the logs (stream in real-time).
    :return: The logs of the container.
    """
    try:
        # Set default namespace if not provided
        if not namespace:
            namespace = "default"

        # Get the API client
        core_v1 = client.CoreV1Api()

        try:
            # Get the pod
            pod = core_v1.read_namespaced_pod(pod_name, namespace)

            # If container is not specified, use the first container
            if not container:
                if pod.spec.containers:
                    container = pod.spec.containers[0].name
                else:
                    return "Error: No containers found in pod"

            # If follow is True, we need to stream the logs
            if follow:
                # Create a streaming request for logs
                logs_stream = core_v1.read_namespaced_pod_log(
                    name=pod_name,
                    namespace=namespace,
                    container=container,
                    follow=True,
                    previous=previous,
                    tail_lines=int(tail) if tail else None,
                    timestamps=timestamps,
                    since_seconds=_parse_since(since) if since else None,
                    _preload_content=False,
                )

                # Stream the logs
                logs = ""
                for line in logs_stream:
                    if isinstance(line, bytes):
                        line = line.decode("utf-8")
                    logs += line

                    # Check if we should stop following (1MB limit)
                    if len(logs) > 1024 * 1024:
                        logs += "\n... log output truncated ...\n"
                        break

                # Close the stream
                logs_stream.close()

                return logs
            else:
                # Get the logs without streaming
                logs = core_v1.read_namespaced_pod_log(
                    name=pod_name,
                    namespace=namespace,
                    container=container,
                    previous=previous,
                    tail_lines=int(tail) if tail else None,
                    timestamps=timestamps,
                    since_seconds=_parse_since(since) if since else None,
                )

                return logs

        except client.exceptions.ApiException as e:
            return f"Error: {str(e)}"
    except Exception as exc:
        return "Error:\n" + str(exc)


def _parse_since(since):
    """
    Parse a since string into seconds.

    :param since: A string like 5s, 2m, 3h, or an absolute timestamp.
    :return: The number of seconds.
    """
    if not since:
        return None

    # Check if it's a relative duration
    match = re.match(r"^(\d+)([smhd])$", since)
    if match:
        value, unit = match.groups()
        value = int(value)

        # Convert to seconds
        if unit == "s":
            return value
        elif unit == "m":
            return value * 60
        elif unit == "h":
            return value * 60 * 60
        elif unit == "d":
            return value * 60 * 60 * 24

    # Check if it's an absolute timestamp
    try:
        # Try to parse as ISO 8601
        dt = datetime.datetime.fromisoformat(since.replace("Z", "+00:00"))

        # Calculate seconds since then
        now = datetime.datetime.now(datetime.timezone.utc)
        return int((now - dt).total_seconds())
    except ValueError:
        # Not a valid timestamp
        return None
