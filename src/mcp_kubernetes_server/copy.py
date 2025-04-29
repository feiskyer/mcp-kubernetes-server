# -*- coding: utf-8 -*-
# pylint: disable=broad-exception-caught
import io
import os
import tarfile
from kubernetes import client
from kubernetes.stream import stream


async def k8s_cp(src_path, dst_path, container=None, namespace=None):
    """
    Copy files and directories to and from containers.

    :param src_path: The source path (local path or pod path in the format pod_name:path).
    :param dst_path: The destination path (local path or pod path in the format pod_name:path).
    :param container: The container name when copying to or from a pod. If not specified, uses the first container.
    :param namespace: The namespace of the pod. If not specified, uses the default namespace.
    :return: The result of the copy operation.
    """
    try:
        # Set default namespace if not provided
        if not namespace:
            namespace = "default"

        # Copy using the Kubernetes Python SDK
        try:
            # Determine if we're copying to or from a pod
            src_is_pod = ":" in src_path
            dst_is_pod = ":" in dst_path

            if src_is_pod and dst_is_pod:
                return "Error: Cannot copy from pod to pod directly"

            # Get the API client
            core_v1 = client.CoreV1Api()

            if src_is_pod:
                # Copying from pod to local
                pod_name, pod_path = src_path.split(":", 1)
                local_path = dst_path

                # Get the pod
                pod = core_v1.read_namespaced_pod(pod_name, namespace)

                # If container is not specified, use the first container
                if not container:
                    if pod.spec.containers:
                        container = pod.spec.containers[0].name
                    else:
                        return "Error: No containers found in pod"

                # Use the exec API to read the file

                # Check if the path is a directory
                is_dir_cmd = f"[ -d {pod_path} ] && echo 'true' || echo 'false'"
                resp = stream(
                    core_v1.connect_get_namespaced_pod_exec,
                    pod_name,
                    namespace,
                    command=["/bin/sh", "-c", is_dir_cmd],
                    container=container,
                    stderr=True,
                    stdin=False,
                    stdout=True,
                    tty=False,
                )

                is_dir = resp.strip() == "true"

                if is_dir:
                    # Create a tarball of the directory
                    # Use more robust tar command that handles spaces and special characters
                    pod_dir = f"$(dirname \"{pod_path}\")"
                    pod_base = f"$(basename \"{pod_path}\")"
                    tar_cmd = f"cd {pod_dir} && tar -cf - {pod_base}"
                    resp = stream(
                        core_v1.connect_get_namespaced_pod_exec,
                        pod_name,
                        namespace,
                        command=["/bin/sh", "-c", tar_cmd],
                        container=container,
                        stderr=True,
                        stdin=False,
                        stdout=True,
                        tty=False,
                        _preload_content=False,
                    )

                    # Read the tarball
                    tarball = b""
                    while resp.is_open():
                        resp.update(timeout=1)
                        if resp.peek_stdout():
                            tarball += resp.read_stdout(timeout=1)

                    # Extract the tarball

                    # Create the destination directory if it doesn't exist
                    os.makedirs(local_path, exist_ok=True)

                    # Extract the tarball
                    with tarfile.open(fileobj=io.BytesIO(tarball), mode="r") as tar:
                        # Check if the tarball has any content
                        if len(tarball) == 0:
                            return f"Error: Failed to create tarball from {pod_path} in pod {pod_name}"

                        # List the contents for debugging
                        file_list = tar.getnames()
                        # Log the file list for debugging
                        print(f"Files in tarball: {file_list}")

                        # Extract the tarball
                        tar.extractall(path=local_path)

                    return f"Successfully copied directory {src_path} to {dst_path}"
                else:
                    # Read the file
                    cat_cmd = f"cat {pod_path}"
                    resp = stream(
                        core_v1.connect_get_namespaced_pod_exec,
                        pod_name,
                        namespace,
                        command=["/bin/sh", "-c", cat_cmd],
                        container=container,
                        stderr=True,
                        stdin=False,
                        stdout=True,
                        tty=False,
                    )

                    # Write the file - convert string response to bytes if needed
                    with open(local_path, "wb") as f:  # Use binary mode
                        if isinstance(resp, str):
                            f.write(resp.encode('utf-8'))
                        else:
                            f.write(resp)

                    return f"Successfully copied file {src_path} to {dst_path}"

            elif dst_is_pod:
                # Copying from local to pod
                local_path = src_path
                pod_name, pod_path = dst_path.split(":", 1)

                # Get the pod
                pod = core_v1.read_namespaced_pod(pod_name, namespace)

                # If container is not specified, use the first container
                if not container:
                    if pod.spec.containers:
                        container = pod.spec.containers[0].name
                    else:
                        return "Error: No containers found in pod"

                # Use the exec API to write the file

                # Check if the local path is a directory
                is_dir = os.path.isdir(local_path)

                if is_dir:
                    # Create a tarball of the directory

                    # Create a tarball in memory
                    tarball_buffer = io.BytesIO()
                    with tarfile.open(fileobj=tarball_buffer, mode="w") as tar:
                        # Add all files in the directory to the tarball
                        # Use basename as arcname to avoid including the full path
                        for root, _, files in os.walk(local_path):
                            for file in files:
                                full_path = os.path.join(root, file)
                                # Calculate the relative path for the archive
                                rel_path = os.path.relpath(full_path, os.path.dirname(local_path))
                                tar.add(full_path, arcname=rel_path)

                        # Print the files added to the tarball for debugging
                        print(f"Added files to tarball for {local_path}")

                    # Get the tarball data
                    tarball_data = tarball_buffer.getvalue()

                    # Check if the tarball has any content
                    if len(tarball_data) == 0:
                        return f"Error: Failed to create tarball from {local_path}"

                    # Create the destination directory
                    mkdir_cmd = f"mkdir -p {pod_path}"
                    resp = stream(
                        core_v1.connect_get_namespaced_pod_exec,
                        pod_name,
                        namespace,
                        command=["/bin/sh", "-c", mkdir_cmd],
                        container=container,
                        stderr=True,
                        stdin=False,
                        stdout=True,
                        tty=False,
                    )

                    # Extract the tarball in the pod
                    # First check if the destination directory exists
                    check_dir_cmd = f"[ -d \"{pod_path}\" ] && echo 'exists' || echo 'not exists'"
                    dir_check = stream(
                        core_v1.connect_get_namespaced_pod_exec,
                        pod_name,
                        namespace,
                        command=["/bin/sh", "-c", check_dir_cmd],
                        container=container,
                        stderr=True,
                        stdin=False,
                        stdout=True,
                        tty=False,
                    )

                    if dir_check.strip() != "exists":
                        error_msg = f"Error: Directory {pod_path} does not exist in pod {pod_name}"
                        return error_msg

                    # Extract the tarball in the pod
                    resp = stream(
                        core_v1.connect_get_namespaced_pod_exec,
                        pod_name,
                        namespace,
                        command=["tar", "-xf", "-", "-C", pod_path],
                        container=container,
                        stderr=True,
                        stdin=True,
                        stdout=True,
                        tty=False,
                        _preload_content=False,
                    )

                    # Write the tarball to stdin
                    resp.write_stdin(tarball_data)

                    # Close the connection
                    resp.close()

                    return f"Successfully copied directory {src_path} to {dst_path}"
                else:
                    # Read the file
                    with open(local_path, "rb") as f:  # Use binary mode
                        file_data = f.read()

                    # Create the destination directory

                    mkdir_cmd = f"mkdir -p {os.path.dirname(pod_path)}"
                    resp = stream(
                        core_v1.connect_get_namespaced_pod_exec,
                        pod_name,
                        namespace,
                        command=["/bin/sh", "-c", mkdir_cmd],
                        container=container,
                        stderr=True,
                        stdin=False,
                        stdout=True,
                        tty=False,
                    )

                    # Write the file
                    write_cmd = f"cat > {pod_path}"
                    resp = stream(
                        core_v1.connect_get_namespaced_pod_exec,
                        pod_name,
                        namespace,
                        command=["/bin/sh", "-c", write_cmd],
                        container=container,
                        stderr=True,
                        stdin=True,
                        stdout=True,
                        tty=False,
                        _preload_content=False,
                    )

                    # Write the file data to stdin
                    resp.write_stdin(file_data)

                    # Close the connection
                    resp.close()

                    return f"Successfully copied file {src_path} to {dst_path}"

            else:
                return "Error: Either source or destination must be a pod path"

        except Exception as e:
            return f"Error: {str(e)}"
    except Exception as exc:
        return "Error:\n" + str(exc)
