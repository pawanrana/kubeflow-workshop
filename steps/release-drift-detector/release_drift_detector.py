import logging, sys

logging.basicConfig(level=logging.INFO, 
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("release-drift-detector.log")])
logger = logging.getLogger(__name__)

import argparse, wo
import os, urllib.parse, pprint
from hydrosdk import sdk


def main(model_name, runtime, payload, metadata, hydrosphere_uri):
    logger.info("Creating a Model object")
    model = sdk.Model()
    logger.info("Adding payload")
    model = model.with_payload(payload)
    logger.info("Adding runtime")
    model = model.with_runtime(runtime)
    logger.info("Adding metadata")
    model = model.with_metadata(metadata)
    logger.info("Assigning name")
    model = model.with_name(model_name)
    logger.info(f"Uploading model to the cluster {hydrosphere_uri}")
    result = model.apply(hydrosphere_uri)
    logger.info(pprint.pformat(result))
    return result


if __name__ == "__main__": 
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-path', required=True)
    parser.add_argument('--model-path', required=True)
    parser.add_argument('--model-name', required=True)
    parser.add_argument('--learning-rate', required=True)
    parser.add_argument('--batch-size', required=True)
    parser.add_argument('--steps', required=True)
    parser.add_argument('--loss', required=True)
    parser.add_argument('--dev', action="store_true", default=False)
    args, unknown = parser.parse_known_args()
    if unknown: 
        logger.warning(f"Parsed unknown args: {unknown}")
    kwargs = dict(vars(args))

    w = wo.Orchestrator(
        default_logs_path="mnist/logs",
        default_params={
            "default.tensorflow_runtime": "hydrosphere/serving-runtime-tensorflow-1.13.1:dev",
            "uri.hydrosphere": "https://dev.k8s.hydrosphere.io",
        },
        dev=args.dev,
    )
    config = w.get_config()
    
    try:

        # Download artifacts
        w.download_prefix(args.model_path, args.model_path)

        # Initialize runtime variables
        dev = kwargs.pop("dev")
        model_name = kwargs.pop("model_name")
        runtime = config["default.tensorflow_runtime"]
        hydrosphere_uri = config["uri.hydrosphere"]
        scheme, bucket, path = w.parse_uri(args.model_path)
        payload = list(map(lambda a: os.path.join(path, a), os.listdir(path)))

        # Execute main script
        result = main(model_name, runtime, payload, kwargs, hydrosphere_uri)

        # Prepare variables for logging
        kwargs["model_version"] = result["modelVersion"]
        kwargs["model_uri"] =  urllib.parse.urljoin(
            config["uri.hydrosphere"], f"/models/{result['model']['id']}/{result['id']}/details")
        
        # Upload artifacts 
        pass
        
    except Exception as e:
        logger.exception("Main execution script failed")
    
    finally: 
        w.log_execution(
            outputs=kwargs,
            logs_bucket=f"{scheme}://{bucket}",
            logs_file="release-drift-detector.log",
        )