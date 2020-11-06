from .error_sources import ErrorSource, WarningSource

from openflexure_microscope.config import user_configuration


def main():
    error_sources = []

    try:
        from sangaboard import Sangaboard
    except ImportError as e:
        error_sources.append(ErrorSource(str(e)))
    else:
        configuration = user_configuration.load()
        stage_type = configuration["stage"].get("type")
        stage_port = configuration["stage"].get("port")

        error_sources.append(
            WarningSource(
                "Stage serial port is not specified in configuration. Application will scan ports for a Sangaboard."
            )
        )

        # If any Sangaboard-based stage is configured for use
        if stage_type in ("SangaBoard", "SangaStage", "SangaDeltaStage"):
            # Try connecting on the specified port
            try:
                _ = Sangaboard(stage_port)
            except FileNotFoundError as e:
                if stage_port:
                    error_sources.append(
                        ErrorSource(
                            f"No {stage_type} device was found on the configured port {stage_port}."
                        )
                    )
                else:
                    error_sources.append(
                        ErrorSource(
                            f"No {stage_type} device was found during port scanning."
                        )
                    )
        else:
            error_sources.append(
                ErrorSource(
                    f"Invalid stage type {stage_type} specified in configuration file."
                )
            )

    return error_sources
