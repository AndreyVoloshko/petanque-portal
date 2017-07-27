# Docker Deployment Scripts for web projects #

#### Requirements
    - docker (for separate containers) Docs here: https://docs.docker.com/engine/installation/
    - ftj (https://bitbucket.org/pixellu-open-source/python-ftj)

##### Additional access
    - VPN configured and connected (for remote deployment)
    - Dropbox/Boxcryptor access (to access credentials files)
    - quay.io access (Docker images repos hoster)
    - Bitbucket access (codebase repos hoster)
    
## Deployment

### Remote envs (prod, stg, prls, htfx)

0. Start Docker demon locally.
1. Add docker machines folders from Dropbox/Boxcryptor "Shared Docker Deployment Assets" folder to your docker folder (~/.docker/machine/machines/)
2. Connect to appropriate VPN using any OpenVPN client. Docker machines must be visible and running in the Terminal.
3. Checkout root project form Bitbucket.
4. Copy appropriate ftj.yml file from Dropbox/Boxcryptor "Shared Docker Deployment Assets" folder to project root.
5. Open Terminal and run one of the following code:
```bash
cd <app_dir>/

bash bash/*ENV*/deploy.sh
OR
bash bash/*ENV*/deploy.sh push
OR
bash bash/*ENV*/deploy.sh push stack_rm
```
Where: *ENV* = stg|prod|htfx|prls

#### Actions during deployment
 1. Code compilation (ftj)
 2. If $1 is "push" then project is pushed to Docker repo
 3. Docker machine activation on local env (its name is taken from the ftj)
 4. If $2 is "stack_rm" docker stack is removed (its name is taken from ftj).
 5. Stack deployment to swarm
 6. Clean up images and containers using docker prune on all instances.
 
### Local envs (dev, tests)
 
 0. Start Docker demon locally.
 1. Checkout root project form Bitbucket.
 4. Copy appropriate ftj.yml file from Dropbox/Boxcryptor "Shared Docker Deployment Assets" folder to project root.
 5. Open Terminal and run one of the following code:
###### Install/Run (Devs env)

```bash
cd <app_dir>/

git clone git@bitbucket.org:touchalbums/px-ps.git .

bash bash/*ENV*/run.sh
```

###### Stop
```bash
cd <app_dir>/
bash bash/*ENV*/stop.sh
```

###### Remove
```bash
cd <app_dir>/
bash bash/*ENV*/remove.sh
```

###### Recreate (runs Stop, Remove, Build, Run)
```bash
cd <app_dir>/
bash bash/*ENV*/recreate.sh
```
Where: *ENV* = dev|tests

#### Actions during deployment
2. Docker composer actions: stop, rm, build, up etc.
