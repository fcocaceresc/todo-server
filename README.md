# Tutorial

1. Clone repository
```bash
git clone git@github.com:fcocaceresc/todo-server.git
```

2. Fill .env_template
3. Change .env_template name to .env
```bash
mv .env_template .env
```
4.1 To run locally:
```bash
make build
make run
```
4.2 To run on an EC2 server:
```bash
make build
make push
make deploy
```