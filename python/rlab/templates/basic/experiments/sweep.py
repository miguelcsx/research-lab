import rlab

lab = rlab.Project()


@lab.experiment("sweep")
def sweep(ctx: rlab.RuntimeContext) -> dict[str, bool]:
    ctx.log_metric("loss", 0.2)
    return {"ok": True}
