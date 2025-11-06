USE " Ctrl+Shift+V " to go into READ-ONLY MODE / PREVIEW

Once you are done testing your project in container use the following commands to cleanup

- Click on the left bottom blue tile which shows "Dev Container: [YOUR-PROJECT-NAME]"
- Choose "Reopen Folder in SSH"
- Now you are outside the container
- Open a terminal session and run the following commands:
  -- To see which containers are currently running, use:
      ```
      docker ps
      ```
  -- If you want just the container IDs or names, you can use:
      ```
      docker ps -q
      ```
  -- If you want ID, Image Name & Container Name:
      ```
      docker ps -a --format "{{.ID}}  {{.Image}}  {{.Names}}"
      ```
- You know which continers to stop now, use the following commands to stop
  -- You know the container’s name or ID:
      ```
      docker stop <container_name_or_id>
      ```
  -- To stop multilple containers:
      ```
      docker stop <container1> <container2> <container3>
      ```
- To verify run the following commands:
  -- To see which containers are currently running, use:
      ```
      docker ps
      ```